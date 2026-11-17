"""Test cho các lỗi tìm được khi nhờ Gemini review repo (đã đối chiếu với code trước khi sửa). Không gọi API thật."""
import json
import subprocess
from types import SimpleNamespace

import imageio_ffmpeg
import pytest

from koc.llm.base import LLM, CallFailed, OutputRejected
from koc.schemas import RationaleSet, ScreenBatch
from koc.stages.select import _improve, video_score
from koc.store import Store

MODELS = {
    "models": {"fake-model": {"provider": "fake", "input_per_m": 1.0, "output_per_m": 2.0}},
    "limits": {"max_usd_per_run": 1.0, "max_attempts": 3, "concurrency": 2},
}


def screen_reply(handles):
    return {"creators": [{"handle": h, "account_kind": "individual_creator", "primary_niche": "skincare_review",
                          "topic_relevance": 8, "content_signals": [], "competitor_brands": [],
                          "brand_safety_flags": [], "fit_note": "ok"} for h in handles]}


class ScriptedAdapter:
    """Trả lời theo kịch bản; ghi lại input của từng lần gọi."""

    def __init__(self, replies):
        self.replies, self.seen = list(replies), []

    def complete(self, *, parts, schema, **kw):
        self.seen.append(parts[0]["text"])
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r(parts) if callable(r) else r, 1000, 100, None


def make_llm(tmp_path, replies):
    llm = LLM(MODELS, Store(tmp_path / "t.db"), "r1")
    llm._adapters["fake"] = adapter = ScriptedAdapter(replies)
    return llm, adapter


# --- 1. video lạc chủ đề -------------------------------------------------------------------------------------------
def test_off_topic_video_gets_no_credit_for_demo_and_texture():
    v = {"is_on_topic": True, "face_on_camera": True, "product_demo_on_skin": True, "shows_texture_or_finish": True,
         "hook_strength": 3, "production_quality": 5, "risky_claims": []}
    off = {**v, "is_on_topic": False}
    # Thoa SỮA TẮM lên da không phải bằng chứng review kem chống nắng: chỉ còn điểm "lộ mặt" trong 4 tiêu chí
    assert video_score(off) == pytest.approx(0.6 * 1 / 4 + 0.2 * 3 / 5 + 0.2)
    assert video_score(v) - video_score(off) == pytest.approx(0.45)


# --- 2. lệnh gọi hỏng vẫn bị tính tiền ---------------------------------------------------------------------------
def test_failed_call_still_records_cost(tmp_path):
    llm, _ = make_llm(tmp_path, [CallFailed("hết max_tokens", 5000, 4000, 0.03)])
    with pytest.raises(CallFailed):
        llm.call(stage="screen", model="fake-model", system="s", parts=[{"type": "text", "text": "[]"}],
                 schema=ScreenBatch, item_ids=["a"])
    assert llm.store.run_cost("r1") == pytest.approx(0.03)


def test_renamed_benchmark_run_reuses_old_measurements(tmp_path):
    """Run input bị đổi tên -> tên vùng cache benchmark đổi theo; vẫn đọc được kết quả đo cũ, không trả tiền lại."""
    store = Store(tmp_path / "t.db")
    kw = dict(stage="screen", model="fake-model", system="s", parts=[{"type": "text", "text": "[]"}],
              schema=ScreenBatch, item_ids=["a"])
    old = LLM(MODELS, store, "bench-final-abc", cache_namespace="bench-final-abc")
    old._adapters["fake"] = ScriptedAdapter([screen_reply([])])
    old.call(**kw)
    new = LLM(MODELS, store, "bench-final-haiku-abc", cache_namespace="bench-final-haiku-abc",
              legacy_namespaces=["bench-final-abc"])
    new._adapters["fake"] = adapter = ScriptedAdapter([])
    assert new.call(**kw).cache_hit and adapter.seen == []


# --- 3. kiểm kết quả TRƯỚC khi lưu cache ---------------------------------------------------------------------------
def test_rejected_output_is_not_cached(tmp_path):
    good, bad = {"summary_vi": "ok", "kocs": []}, {"summary_vi": "sai", "kocs": []}
    llm, adapter = make_llm(tmp_path, [bad, good])
    kw = dict(stage="rationale", model="fake-model", system="s", parts=[{"type": "text", "text": "x"}],
              schema=RationaleSet, item_ids=["a"], validate=lambda d: "sai" if d["summary_vi"] == "sai" else None)
    with pytest.raises(OutputRejected):
        llm.call(**kw)
    assert llm.call(**kw).data == good          # không đọc lại kết quả sai từ cache
    assert len(adapter.seen) == 2
    assert llm.store.run_cost("r1") > 0          # lần bị loại vẫn ghi tiền


def test_rationale_retries_once_when_citation_invented(tmp_path):
    from koc.stages import rationale
    packs = [{"handle": "a", "evidence": {"M:gmv": "x"}}]
    koc = {"handle": "a", "reason_vi": "r", "risks_vi": "r", "brief_suggestion_vi": "b"}
    bad = {"summary_vi": "s", "kocs": [{**koc, "evidence_refs": ["V:999"]}]}
    good = {"summary_vi": "s", "kocs": [{**koc, "evidence_refs": ["M:gmv"]}]}
    llm, adapter = make_llm(tmp_path, [bad, good])
    campaign = {"product": "kem chống nắng", "target_gender": "female", "target_age_min": 18, "target_age_max": 30,
                "budget_vnd": 30_000_000, "n_koc": 1, "market": "VN"}
    out = rationale._write_chunk(llm, packs, {"model": "fake-model"}, campaign)
    assert out == good and len(adapter.seen) == 2


# --- 4. cache sàng lọc theo từng creator -------------------------------------------------------------------------
def test_screen_reuses_each_creator_when_batch_shifts(tmp_path, monkeypatch):
    from koc.stages import screen
    monkeypatch.setattr(screen, "load_prompt", lambda *a, **k: "prompt")
    monkeypatch.setattr(screen, "prompt_vars", lambda c: {})
    reply = lambda parts: screen_reply([p["handle"] for p in json.loads(parts[0]["text"])])  # noqa: E731
    llm, adapter = make_llm(tmp_path, [reply, reply])
    details = {h: {"bio": h} for h in "abcde"}
    route = {"model": "fake-model"}
    screen.screen_batch(llm, list("abcd"), details, route, {})
    # Tuần sau "e" mới chen vào đầu danh sách -> lô thành [e, a, b, c]: chỉ "e" phải gửi cho model
    out = screen.screen_batch(llm, list("eabc"), details, route, {})
    assert set(out) == set("eabc")
    assert [p["handle"] for p in json.loads(adapter.seen[1])] == ["e"]


# --- 5. chọn KOC: đổi trong cùng nhóm liên hệ ------------------------------------------------------------------------
def test_improve_can_swap_within_same_contact_group():
    sel = [{"handle": "a", "final_score": 0.5, "est_cost_vnd": 3, "contact_group": "g"},
           {"handle": "x", "final_score": 0.9, "est_cost_vnd": 3, "contact_group": None}]
    pool = sel + [{"handle": "b", "final_score": 0.8, "est_cost_vnd": 3, "contact_group": "g"}]
    out = {c["handle"] for c in _improve(pool, sel, budget_vnd=6)}
    assert out == {"b", "x"}       # b thay a: cùng nhóm g nên vẫn chỉ 1 kênh của nhóm


# --- 6. Gemini: effort và giá token âm thanh -------------------------------------------------------------------------
def test_gemini_applies_effort_and_prices_audio_separately():
    from koc.llm.gemini_adapter import THINKING_HEADROOM, cost_usd, thinking_config
    assert THINKING_HEADROOM["high"] > THINKING_HEADROOM["low"] > 0   # chừa chỗ cho token suy nghĩ
    assert thinking_config("low").thinking_level.name == "LOW"
    assert thinking_config("high").thinking_level.name == "HIGH"
    assert thinking_config(None) is None
    modality = lambda name: SimpleNamespace(name=name)  # noqa: E731
    usage = SimpleNamespace(prompt_token_count=10_000, candidates_token_count=500, thoughts_token_count=500,
                            prompt_tokens_details=[SimpleNamespace(modality=modality("VIDEO"), token_count=6_000),
                                                   SimpleNamespace(modality=modality("AUDIO"), token_count=4_000)])
    cfg = {"input_per_m": 0.25, "audio_input_per_m": 0.50, "output_per_m": 1.50}
    assert cost_usd(usage, cfg) == pytest.approx((6_000 * 0.25 + 4_000 * 0.50 + 1_000 * 1.50) / 1e6)


# --- 7. thứ tự gộp danh sách nguồn ----------------------------------------------------------------------------------
def test_comparable_revenue_list_wins_over_alphabetical_order(tmp_path):
    from koc.sources.kalodata import load_creator_list
    for name in ("creators_list_content", "creators_list_video"):
        (tmp_path / f"{name}.json").write_text(json.dumps({"creators": [{"handle": "a", "rank": 1, "src": name}]}),
                                               encoding="utf-8")
    paths = sorted(tmp_path.glob("*.json"))          # theo tên file: _content đứng trước _video
    c = load_creator_list(paths)["creators"][0]
    assert c["revenue_basis"] == "creators_list_video" and c["src"] == "creators_list_video"


# --- 8. âm thanh .m4a được đổi sang .mp3 ---------------------------------------------------------------------------
def test_m4a_audio_converted_to_mp3(tmp_path):
    from koc.media import to_mp3
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=16000:cl=mono", "-t", "1", str(tmp_path / "123.m4a")], check=True)
    mp3 = to_mp3(tmp_path, "123")
    assert mp3 == tmp_path / "123.mp3" and mp3.stat().st_size > 0
