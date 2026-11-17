"""Adapter DeepSeek (API định dạng OpenAI, base_url https://api.deepseek.com).

DeepSeek chưa có structured output theo schema như Claude/Gemini: dùng JSON mode
(response_format=json_object), đưa schema vào prompt, rồi tự kiểm bằng Pydantic.
deepseek-flash đọc được ảnh (tối đa 1024 token/ảnh); deepseek-v4-pro chỉ đọc text.
"""
import base64
import json
import os
from pathlib import Path

from openai import OpenAI

from koc.llm.base import CallFailed

EFFORT_MAP = {"low": "low", "medium": "high", "high": "high", "xhigh": "max", "max": "max"}
# Token suy nghĩ tính vào max_tokens -> cộng thêm chỗ cho suy nghĩ, kẻo hết chỗ trước khi viết JSON
THINKING_HEADROOM = {"low": 4000, "high": 16000, "max": 32000}


class DeepSeekAdapter:
    def __init__(self):
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("Chưa có DEEPSEEK_API_KEY trong .env")
        self.client = OpenAI(api_key=key, base_url="https://api.deepseek.com", max_retries=3)

    @staticmethod
    def _content(parts: list[dict]) -> list[dict]:
        out = []
        for p in parts:
            if p["type"] == "text":
                out.append({"type": "text", "text": p["text"]})
            elif p["type"] == "image":
                b64 = base64.b64encode(Path(p["path"]).read_bytes()).decode()
                out.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
            else:
                raise ValueError(f"DeepSeek không nhận '{p['type']}'")
        return out

    def complete(self, *, model, system, parts, schema, effort, max_tokens, model_cfg):
        schema_text = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        sys_prompt = (system + "\n\nChỉ trả về một đối tượng json hợp lệ theo đúng JSON Schema sau "
                      "(không thêm chữ nào ngoài json):\n" + schema_text)
        level = EFFORT_MAP.get(effort or "high", "high")
        kwargs = dict(
            model=model,
            messages=[{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": self._content(parts)}],
            response_format={"type": "json_object"},
            max_tokens=max_tokens + THINKING_HEADROOM[level],
            extra_body={"thinking": {"type": "enabled"}},
            reasoning_effort=level,
        )
        prompt_tokens = completion_tokens = hit = 0
        last_err = None
        for _ in range(2):                      # JSON mode đôi khi trả rỗng/hỏng -> thử lại 1 lần
            resp = self.client.chat.completions.create(**kwargs)
            u = resp.usage
            prompt_tokens += u.prompt_tokens
            completion_tokens += u.completion_tokens
            hit += getattr(u, "prompt_cache_hit_tokens", 0) or 0
            text = (resp.choices[0].message.content or "").strip()
            try:
                if not text:
                    raise ValueError(f"JSON rỗng (finish_reason={resp.choices[0].finish_reason})")
                data = schema.model_validate(json.loads(text)).model_dump()
                break
            except Exception as e:
                last_err = e
            data = None
        miss = prompt_tokens - hit
        cost = (miss * model_cfg["input_per_m"] + hit * model_cfg.get("cache_hit_per_m", model_cfg["input_per_m"])
                + completion_tokens * model_cfg["output_per_m"]) / 1_000_000
        if data is None:   # 2 lần đều hỏng nhưng vẫn bị tính tiền cả 2 lần
            raise CallFailed(f"DeepSeek trả JSON không hợp lệ sau 2 lần: {last_err}", prompt_tokens, completion_tokens, cost)
        return data, prompt_tokens, completion_tokens, cost
