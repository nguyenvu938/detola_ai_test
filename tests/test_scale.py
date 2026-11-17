"""Test khả năng mở rộng: bài chọn với n lớn, xếp hạng nhanh, phễu tỷ lệ theo số KOC, chia lô viết lý do,
và chạy nguyên pipeline trên dữ liệu giả lập (model giả, không gọi mạng)."""
import random
import time

from koc import scale
from koc.stages.prefilter import funnel_caps, percentile_ranks
from koc.stages.rationale import write_rationale
from koc.stages.select import _choose_exact, _choose_large, choose

TIERS = [3_250_000, 3_750_000, 8_000_000, 11_000_000]


def make_pool(n, rng, group_rate=0.1):
    pool = [{"handle": f"h{i}", "final_score": round(rng.uniform(0.5, 0.9), 3), "est_cost_vnd": rng.choice(TIERS),
             "contact_group": f"g{rng.randint(0, n // 10)}" if rng.random() < group_rate else None} for i in range(n)]
    return sorted(pool, key=lambda c: c["final_score"], reverse=True)


def score(res):
    return sum(c["final_score"] for c in res["selected"])


def test_large_selection_close_to_exhaustive():
    """Thuật toán cho n lớn, chạy trên bài nhỏ, phải gần bằng vét cạn (đáp án đúng)."""
    rng = random.Random(1)
    ratios = []
    for _ in range(200):
        pool = make_pool(12, rng)
        budget = rng.choice([20_000_000, 30_000_000, 40_000_000])
        exact, approx = _choose_exact(pool, 5, budget, 12), _choose_large(pool, 5, budget)
        assert approx["total_cost_vnd"] <= budget
        if exact["selected"]:
            assert len(approx["selected"]) == len(exact["selected"])
            ratios.append(score(approx) / score(exact))
    assert min(ratios) >= 0.95 and sum(ratios) / len(ratios) >= 0.995


def test_large_selection_500_koc_respects_budget_and_groups():
    rng = random.Random(2)
    pool = make_pool(4000, rng)
    t0 = time.perf_counter()
    res = choose(pool, 500, 500 * 6_000_000)
    assert time.perf_counter() - t0 < 10
    sel = res["selected"]
    assert len(sel) == 500 and res["total_cost_vnd"] <= 500 * 6_000_000
    groups = [c["contact_group"] for c in sel if c["contact_group"]]
    assert len(groups) == len(set(groups))           # tối đa 1 KOC mỗi nhóm liên hệ


def test_large_selection_shrinks_when_budget_too_small():
    pool = make_pool(100, random.Random(3), group_rate=0)
    res = choose(pool, 50, 20 * 3_250_000)            # chỉ đủ tiền cho 20 người rẻ nhất
    assert len(res["selected"]) == 20 and res["total_cost_vnd"] <= 20 * 3_250_000


def test_percentile_ranks_same_as_brute_force():
    rng = random.Random(4)
    vals = [rng.choice([None, 1, 2, 2, 3, 5, 5, 5, 8]) for _ in range(300)]
    known = [v for v in vals if v is not None]
    brute = [0.5 if v is None else (sum(k < v for k in known) + 0.5 * sum(k == v for k in known)) / len(known)
             for v in vals]
    assert percentile_ranks(vals) == brute


def test_funnel_caps_scale_with_n_koc():
    camp = {"campaign": {"n_koc": 5},
            "prefilter": {"enrich_per_koc": 12, "enrich_quota": {"a": 20, "b": 10, "c": 20, "d": 10}},
            "funnel": {"screen_per_koc": 8, "video_per_koc": 2}}
    c5 = funnel_caps(camp)
    assert (c5["enrich"], c5["screen"], c5["video"]) == (60, 40, 10) and c5["quota"] == {"a": 20, "b": 10, "c": 20, "d": 10}
    camp["campaign"]["n_koc"] = 500
    c500 = funnel_caps(camp)
    assert (c500["enrich"], c500["screen"], c500["video"]) == (6000, 4000, 1000) and c500["quota"]["a"] == 2000


class CountingLLM:
    """Giả lập LLM.call cho bước viết lý do: trích 1 mã bằng chứng có thật của từng KOC."""
    def __init__(self):
        self.calls = 0

    def call(self, *, parts, item_ids, **kw):
        import json
        self.calls += 1
        packs = json.loads(parts[0]["text"])

        class R:
            data = {"summary_vi": "ok", "kocs": [{"handle": p["handle"], "reason_vi": "", "risks_vi": "",
                                                  "brief_suggestion_vi": "", "evidence_refs": ["M:gmv"]} for p in packs]}
        return R


def test_rationale_split_into_batches_for_large_sets():
    rows, screens, videos = [], {}, {}
    for i in range(23):
        h = f"k{i}"
        rows.append({"handle": h, "followers": 50_000, "est_cost_vnd": 3_250_000, "final_score": 0.7,
                     "category_gmv_vnd": 10**8, "gmv_basis": "creators_list", "audience_source": "x"})
        screens[h] = {"account_kind": "individual_creator", "primary_niche": "skincare_review", "topic_relevance": 7,
                      "fit_note": ""}
        videos[h] = {"video_id": str(i), "kind": "video",
                     "analysis": {"summary_vi": "", "evidence": [{"at": "00:01", "observation": "x"}]}}
    llm = CountingLLM()
    out = write_rationale(llm, rows, screens, videos, {"model": "m", "batch_size": 10},
                          {"product": "kem chống nắng", "target_gender": "female", "target_age_min": 18,
                           "target_age_max": 30, "budget_vnd": 138_000_000, "n_koc": 23},
                          concurrency=3)
    assert llm.calls == 3                                 # 10 + 10 + 3
    assert len(out["rationale"]["kocs"]) == 23 and out["citation_check"]["valid_rate"] == 1.0


def test_full_pipeline_at_scale_and_resume(tmp_path, monkeypatch):
    """Nguyên pipeline trên 500 creator giả (20 KOC): chọn đủ; sập giữa chừng rồi chạy lại không gọi lặp item nào."""
    monkeypatch.setattr(scale, "SCALE_DIR", tmp_path)
    profile = scale.per_item_profile()
    clean = scale.run_scenario(20, seed=3, profile=profile)
    assert clean["selected"] == 20 and clean["booking_vnd"] <= clean["budget_vnd"]
    assert clean["llm_calls"]["rationale"] == 2           # 20 KOC / 10 mỗi lần gọi
    resumed = scale.run_scenario(20, seed=3, profile=profile, crash_after=clean["llm_calls_total"] // 2, tag="-r")
    assert resumed["crashed_then_resumed"] and resumed["duplicate_paid_items"] == 0
    assert resumed["llm_calls_total"] == clean["llm_calls_total"]
