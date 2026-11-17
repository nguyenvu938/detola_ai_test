"""Lớp gọi LLM dùng chung cho mọi nhà cung cấp.

Mọi lần gọi model đều đi qua `LLM.call()`, nơi xử lý 4 việc chung:
  1. Cache theo hash (model + effort + prompt + input + schema): gọi lại cùng input = 0 đồng.
  2. Chặn ngân sách: tổng chi phí run vượt `max_usd_per_run` thì dừng. Chạy song song thì có thể vượt
     tối đa (số luồng × chi phí 1 lần gọi), vì các lần gọi đang chạy dở chưa ghi chi phí.
  3. Ghi sổ token / chi phí / độ trễ vào SQLite (bảng llm_calls), kể cả lần gọi hỏng mà hãng vẫn tính tiền.
  4. Giả lập sự cố (--crash-after N) để chứng minh khả năng resume.
Phần riêng của từng nhà cung cấp (định dạng request, đọc usage) nằm trong adapter.
"""
import hashlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from koc.store import Store, cache_key

# Đổi CÁCH adapter gọi API (vd Gemini bắt đầu áp dụng effort) thì tăng phiên bản ở đây:
# kết quả cũ trong cache được tạo bằng cách gọi cũ nên không được dùng lại.
ADAPTER_VERSION = {"gemini": "thinking-level"}


class BudgetExceeded(RuntimeError):
    pass


class SimulatedCrash(RuntimeError):
    pass


class CallFailed(RuntimeError):
    """Hãng đã xử lý (và tính tiền) nhưng kết quả không dùng được: hết max_tokens, JSON hỏng, từ chối...
    Mang theo token và chi phí để vẫn ghi đúng vào sổ."""

    def __init__(self, message: str, input_tokens: int = 0, output_tokens: int = 0, cost_usd: float = 0.0):
        super().__init__(message)
        self.input_tokens, self.output_tokens, self.cost_usd = input_tokens, output_tokens, cost_usd


class OutputRejected(RuntimeError):
    """Kết quả đúng schema nhưng code kiểm tra thấy sai (vd trích dẫn bằng chứng không có thật). Không lưu cache."""


@dataclass
class Usage:
    input_tokens: int          # tổng token vào (gồm phần đọc từ prompt cache)
    output_tokens: int         # gồm thinking token
    cost_usd: float


@dataclass
class LLMResult:
    data: dict
    model: str
    usage: Usage
    latency_ms: int
    cache_hit: bool
    saved_usd: float = 0.0     # cache hit: chi phí gốc của lần gọi thật đã tạo ra kết quả này


def file_digest(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def price(model_cfg: dict, input_tokens: float, output_tokens: float) -> float:
    return (input_tokens * model_cfg["input_per_m"] + output_tokens * model_cfg["output_per_m"]) / 1_000_000


class LLM:
    def __init__(self, models_cfg: dict, store: Store, run_id: str, crash_after: int | None = None,
                 use_cache: bool = True, cache_namespace: str | None = None, legacy_namespaces: list[str] = ()):
        self.models = models_cfg["models"]
        self.limits = models_cfg["limits"]
        self.store = store
        self.run_id = run_id
        self.crash_after = crash_after
        self.use_cache = use_cache       # False = đo chi phí "chạy nguội" (vẫn ghi cache cho lần sau)
        # Vùng cache riêng (benchmark): mỗi lần đo trả tiền thật đúng 1 lần cho mỗi item, chạy lại thì không trả lại
        self.cache_namespace = cache_namespace
        # Vùng cache cũ của CÙNG phép đo (vd run input bị đổi tên): đọc được thì chép sang vùng mới, không trả tiền lại
        self.legacy_namespaces = list(legacy_namespaces)
        self.real_calls = 0
        self._started = 0                # số lần gọi thật đã BẮT ĐẦU (để --crash-after đúng cả khi chạy song song)
        self._adapters = {}
        self._lock = threading.Lock()    # nhiều luồng cùng gọi: tạo adapter 1 lần, kiểm ngân sách/đếm lượt không lẫn

    def _adapter(self, provider: str):
        with self._lock:
            return self._adapter_unlocked(provider)

    def _adapter_unlocked(self, provider: str):
        if provider not in self._adapters:
            if provider == "anthropic":
                from koc.llm.anthropic_adapter import AnthropicAdapter
                self._adapters[provider] = AnthropicAdapter()
            elif provider == "gemini":
                from koc.llm.gemini_adapter import GeminiAdapter
                self._adapters[provider] = GeminiAdapter()
            elif provider == "deepseek":
                from koc.llm.deepseek_adapter import DeepSeekAdapter
                self._adapters[provider] = DeepSeekAdapter()
            else:
                raise NotImplementedError(f"Chưa có adapter cho provider '{provider}' (thêm khi có API key)")
        return self._adapters[provider]

    def call(self, *, stage: str, model: str, system: str, parts: list[dict], schema: type[BaseModel],
             item_ids: list[str], effort: str | None = None, max_tokens: int = 4000,
             validate: Callable[[dict], str | None] | None = None) -> LLMResult:
        """parts: [{"type": "text", "text": ...}, {"type": "image", "path": ...}, {"type": "video", "path": ..., "clip_seconds": 60}]
        validate: hàm kiểm kết quả bằng code, trả chuỗi mô tả lỗi nếu sai -> ném OutputRejected, KHÔNG lưu cache
        (lưu thì lần gọi lại sẽ đọc đúng kết quả sai đó từ cache)."""
        mcfg = self.models[model]
        # Khóa cache dùng hash nội dung file, không dùng đường dẫn.
        parts_key = [{**p, "path": file_digest(p["path"])} if "path" in p else p for p in parts]
        key_parts = (model, effort, system, parts_key, schema.__name__, schema.model_json_schema())
        if ADAPTER_VERSION.get(mcfg["provider"]):
            key_parts += (ADAPTER_VERSION[mcfg["provider"]],)
        key = cache_key(*key_parts, self.cache_namespace) if self.cache_namespace else cache_key(*key_parts)

        cached = self.store.cache_get(key) if self.use_cache else None
        for ns in self.legacy_namespaces if cached is None and self.use_cache else []:
            cached = self.store.cache_get(cache_key(*key_parts, ns))
            if cached is not None:
                self.store.cache_put(key, cached)
                break
        if cached is not None:
            # Định dạng mới: {"__data__": ..., "__cost__": ...}; định dạng cũ: chỉ có data (không biết chi phí gốc)
            data, saved = (cached["__data__"], cached.get("__cost__", 0.0)) if "__data__" in cached else (cached, 0.0)
            self.store.log_call(self.run_id, stage, model, item_ids, 0, 0, 0.0, 0, cache_hit=True, ok=True,
                                saved_usd=saved)
            return LLMResult(data, model, Usage(0, 0, 0.0), 0, cache_hit=True, saved_usd=saved)

        with self._lock:
            if self.store.run_cost(self.run_id) >= self.limits["max_usd_per_run"]:
                raise BudgetExceeded(f"Run đã tiêu ≥ ${self.limits['max_usd_per_run']} – dừng để tránh vượt ngân sách")
            if self.crash_after is not None and self._started >= self.crash_after:
                raise SimulatedCrash(f"Giả lập sự cố sau {self._started} lần gọi model")
            self._started += 1

        adapter = self._adapter(mcfg["provider"])
        t0 = time.perf_counter()
        try:
            data, in_tok, out_tok, cost_override = adapter.complete(
                model=model, system=system, parts=parts, schema=schema, effort=effort,
                max_tokens=max_tokens, model_cfg=mcfg,
            )
        except Exception as e:
            latency = int((time.perf_counter() - t0) * 1000)
            # CallFailed: hãng đã tính tiền -> ghi đúng số tiền; lỗi khác (mạng, key...) coi như 0 đồng
            f = e if isinstance(e, CallFailed) else CallFailed(str(e))
            self.store.log_call(self.run_id, stage, model, item_ids, f.input_tokens, f.output_tokens, f.cost_usd,
                                latency, cache_hit=False, ok=False)
            raise
        latency = int((time.perf_counter() - t0) * 1000)
        with self._lock:
            self.real_calls += 1
        cost = cost_override if cost_override is not None else price(mcfg, in_tok, out_tok)
        problem = validate(data) if validate else None
        self.store.log_call(self.run_id, stage, model, item_ids, in_tok, out_tok, cost, latency, cache_hit=False,
                            ok=problem is None)
        if problem:
            raise OutputRejected(problem)
        self.store.cache_put(key, {"__data__": data, "__cost__": cost})
        return LLMResult(data, model, Usage(in_tok, out_tok, cost), latency, cache_hit=False)
