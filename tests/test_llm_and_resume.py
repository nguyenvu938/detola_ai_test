"""Test lớp LLM (cache, ngân sách, giả lập sự cố) và resume của pipeline. API được giả lập (mock)."""
import pytest

from koc import pipeline
from koc.llm.base import LLM, BudgetExceeded, SimulatedCrash
from koc.schemas import ScreenBatch
from koc.store import Store

MODELS = {
    "models": {"fake-model": {"provider": "fake", "input_per_m": 1.0, "output_per_m": 2.0, "video": False}},
    "limits": {"max_usd_per_run": 1.0, "max_attempts": 3, "concurrency": 2},
    "routing": {
        "screen": {"model": "fake-model", "batch_size": 2},
        "video": {"model": "fake-model"},
        "rationale": {"model": "fake-model"},
    },
}


class FakeAdapter:
    def __init__(self):
        self.calls = 0

    def complete(self, *, model, system, parts, schema, effort, max_tokens, model_cfg):
        self.calls += 1
        if schema is ScreenBatch:
            import json
            handles = [p["handle"] for p in json.loads(parts[0]["text"])]
            data = {"creators": [{"handle": h, "account_kind": "individual_creator", "primary_niche": "skincare_review",
                                  "topic_relevance": 8, "content_signals": [], "competitor_brands": [],
                                  "brand_safety_flags": [], "fit_note": "ok"} for h in handles]}
        else:
            data = {"summary_vi": "ok", "kocs": []}
        return data, 1000, 100, None


def make_llm(tmp_path, crash_after=None, max_usd=1.0):
    store = Store(tmp_path / "t.db")
    models = {**MODELS, "limits": {**MODELS["limits"], "max_usd_per_run": max_usd}}
    llm = LLM(models, store, "r1", crash_after=crash_after)
    fake = FakeAdapter()
    llm._adapters["fake"] = fake
    return llm, store, fake


def screen_parts(handles):
    import json
    return [{"type": "text", "text": json.dumps([{"handle": h} for h in handles])}]


def test_cache_hit_costs_nothing(tmp_path):
    llm, store, fake = make_llm(tmp_path)
    kw = dict(stage="screen", model="fake-model", system="s", parts=screen_parts(["a"]), schema=ScreenBatch, item_ids=["a"])
    r1 = llm.call(**kw)
    r2 = llm.call(**kw)
    assert fake.calls == 1
    assert r2.cache_hit and r2.usage.cost_usd == 0
    assert store.run_cost("r1") == pytest.approx((1000 * 1.0 + 100 * 2.0) / 1e6)


def test_budget_guard_stops_calls(tmp_path):
    llm, _, _ = make_llm(tmp_path, max_usd=0.0)
    with pytest.raises(BudgetExceeded):
        llm.call(stage="screen", model="fake-model", system="s", parts=screen_parts(["a"]), schema=ScreenBatch, item_ids=["a"])


def test_crash_then_resume_skips_done_items(tmp_path, monkeypatch):
    """Chạy pipeline, 'sập' sau 1 lần gọi model; chạy lại thì chỉ làm phần còn thiếu."""
    creators = [{"handle": f"c{i}", "nickname": f"c{i}", "followers": 50_000, "revenue_vnd": 10**8 + i,
                 "content_views": 10**6, "engagement_rate": 0.01, "kalodata_id": str(i)} for i in range(4)]
    detail = lambda h: {"handle": h, "creator_type": "INDEPENDENT", "followers": 50_000,  # noqa: E731
                        "follower_gender": {"female": 0.9}, "follower_age": {"18-24": 0.6, "25-34": 0.3},
                        "videos": [{"video_id": "1", "views": 1000, "is_ad": False}]}
    monkeypatch.setattr(pipeline, "load_creator_list", lambda: {"creators": creators})
    monkeypatch.setattr(pipeline, "load_creator_detail", detail)
    video_calls = []

    def fake_video(llm, d, campaign, route, mcfg):
        video_calls.append(d["handle"])
        return {"video_id": "1", "url": "u", "analysis": {
            "is_on_topic": True, "face_on_camera": True, "product_demo_on_skin": True,
            "shows_texture_or_finish": True, "hook_strength": 4, "production_quality": 4, "risky_claims": [],
            "summary_vi": "ok", "evidence": []}}
    monkeypatch.setattr(pipeline, "analyze_creator", fake_video)
    monkeypatch.setattr(pipeline, "write_rationale", lambda *a, **k: {"rationale": {"summary_vi": "", "kocs": []}})

    cfg = {
        "campaign": {
            "campaign": {"n_koc": 2, "budget_vnd": 30_000_000, "topic_keywords": ["spf"], "product": "kem chống nắng",
                         "target_gender": "female", "target_age_min": 18, "target_age_max": 30},
            "prefilter": {**{"min_followers": 10_000, "max_followers": 500_000, "exclude_name_patterns": []},
                          "max_for_enrich": 4},
            "audience": {"min_target_gender_share": 0.55},
            "funnel": {"max_for_screen": 4, "max_for_video": 3, "eligible_kinds": ["individual_creator"],
                       "min_relevance": 3, "min_final_score": 0.0},
            "weights": {"metric": {"audience": 0.5, "category_gmv": 0.5, "conversion": 0, "views_per_follower": 0,
                                   "engagement": 0, "organic": 0},
                        "final": {"metric": 0.5, "screen": 0.2, "video": 0.3}},
        },
        "models": MODELS,
        "market": {"rate_card": [{"min_followers": 0, "max_followers": 10**9, "fee_vnd": 5_000_000}]},
    }
    store = Store(tmp_path / "p.db")
    log = lambda *a: None  # noqa: E731

    # Lần 1: sập sau 1 lần gọi model (batch screen đầu tiên xong, batch thứ 2 chưa)
    llm = LLM(MODELS, store, "run", crash_after=1)
    fake = FakeAdapter()
    llm._adapters["fake"] = fake
    with pytest.raises(SimulatedCrash):
        pipeline.run(cfg, store, "run", llm, log=log)
    assert fake.calls == 1
    assert len(store.stage_outputs("run", "screen")) == 2

    # Lần 2: resume – chỉ gọi model cho batch còn thiếu
    llm2 = LLM(MODELS, store, "run")
    fake2 = FakeAdapter()
    llm2._adapters["fake"] = fake2
    result = pipeline.run(cfg, store, "run", llm2, log=log)
    assert fake2.calls == 1                      # chỉ 1 batch screen còn lại
    assert len(store.stage_outputs("run", "screen")) == 4
    assert len(result["choice"]["selected"]) == 2

    # Lần 3: mọi thứ đã xong -> không gọi model, không phân tích lại video
    n_video = len(video_calls)
    llm3 = LLM(MODELS, store, "run")
    fake3 = FakeAdapter()
    llm3._adapters["fake"] = fake3
    pipeline.run(cfg, store, "run", llm3, log=log)
    assert fake3.calls == 0
    assert len(video_calls) == n_video
