"""Test phần chấm của benchmark (không gọi API)."""
from koc.benchmark import agreement, consensus


def test_consensus_majority_and_median():
    a = {"x": {"kind": "creator", "score": 8}}
    b = {"x": {"kind": "shop", "score": 4}}
    c = {"x": {"kind": "creator", "score": 6}}
    ref = consensus([a, b, c], exact=["kind"], num=["score"])
    assert ref == {"x": {"kind": "creator", "score": 6}}


def test_agreement_exact_and_mae():
    ref = {"x": {"kind": "creator", "score": 6}, "y": {"kind": "shop", "score": 2}}
    out = {"x": {"kind": "creator", "score": 8}, "y": {"kind": "creator", "score": 2}}
    a = agreement(out, ref, exact=["kind"], num=["score"])
    assert a["kind"] == 0.5 and a["exact_avg"] == 0.5
    assert a["score_mae"] == 1.0


def test_consensus_skips_ties_and_needs_two_refs():
    a = {"x": {"kind": "creator", "score": 8}, "only_a": {"kind": "shop", "score": 1}}
    b = {"x": {"kind": "shop", "score": 4}}
    ref = consensus([a, b], exact=["kind"], num=["score"])
    assert "only_a" not in ref                 # chỉ 1 tham chiếu -> không có nhãn
    assert "kind" not in ref["x"]              # hoà 1-1 -> bỏ trường
    assert ref["x"]["score"] == 6
    out = {"x": {"kind": "creator", "score": 6}}
    assert agreement(out, ref, exact=["kind"], num=["score"])["exact_avg"] is None


def test_recommend_picks_cheapest_that_meets_threshold():
    from koc.benchmark import recommend
    b = {"reference_models": ["big"], "reference_effort": "high", "min_agreement": 0.9}
    run = lambda m, cost, agree, eff="low": {"model": m, "effort": eff, "cost_usd": cost, "errors": [],  # noqa: E731
                                            "agreement_vs_ref": {"exact_avg": agree}, "avg_latency_ms": 1000}
    rep = {"stages": {
        "screen": [run("cheap_bad", 0.001, 0.70), run("cheap_ok", 0.002, 0.92), run("big", 0.10, 0.98),
                   run("big", 0.20, 1.0, "high")],
        "video": [run("cheap_ok", 0.01, 0.95), run("big", 0.30, 0.97)],
        "rationale": [{**run("cheap_ok", 0.002, None), "citation_check": {"valid_rate": 1.0}},
                      {**run("big", 0.05, None), "citation_check": {"valid_rate": 1.0}}],
    }}
    result = {"choice": {"selected": [1, 2, 3, 4, 5]}, "funnel": {"screened": 10, "video_analyzed": 5},
              "screens": {str(i): {} for i in range(10)}, "videos": {str(i): {} for i in range(5)}}
    routing = {"screen": {"model": "big"}, "video": {"model": "big"}, "rationale": {"model": "big"}}
    rec = recommend(rep, result, b, routing)
    assert rec["stages"]["screen"]["model"] == "cheap_ok"        # rẻ nhất đạt >= 90%, không phải cheap_bad
    assert rec["stages"]["screen"]["best_quality"]["model"] == "big"   # bản high (tham chiếu) không được tính
    assert rec["stages"]["rationale"]["model"] == "cheap_ok"
    plans = {p["name"]: p["usd_500_koc"] for p in rec["plans"]}
    assert plans["Đề xuất (theo benchmark)"] < plans["Lúc chạy run ?"]     # rẻ hơn định tuyến cũ (big)


def test_compare_by_provider_and_single_provider_plans():
    """Bảng theo hãng: mỗi hãng lấy model rẻ nhất đạt ngưỡng; có phương án 'chỉ dùng 1 hãng' và tỷ lệ chi phí theo hãng."""
    from koc.benchmark import recommend
    b = {"reference_models": [], "reference_effort": "high", "min_agreement": 0.9}
    run = lambda m, cost, agree: {"model": m, "effort": "low", "cost_usd": cost, "errors": [],  # noqa: E731
                                  "agreement_vs_ref": {"exact_avg": agree, "n": 4}, "avg_latency_ms": 1000}
    rat = lambda m, cost: {**run(m, cost, None), "citation_check": {"valid_rate": 1.0}}  # noqa: E731
    rep = {"stages": {
        "screen": [run("claude-a", 0.002, 0.95), run("gemini-a", 0.001, 0.80), run("gemini-b", 0.01, 1.0),
                   run("deepseek-a", 0.004, 0.91)],
        "video": [run("claude-a", 0.01, 0.90), run("gemini-a", 0.02, 0.98), run("deepseek-a", 0.03, 0.90)],
        "rationale": [rat("claude-a", 0.003), rat("gemini-a", 0.002), rat("deepseek-a", 0.006)],
    }}
    result = {"choice": {"selected": [1]}, "funnel": {"screened": 4, "video_analyzed": 2}, "run_id": "r",
              "screens": {str(i): {} for i in range(4)}, "videos": {str(i): {} for i in range(2)}}
    routing = {st: {"model": "claude-a"} for st in ("screen", "video", "rationale")}
    rec = recommend(rep, result, b, routing, {"gemini-a": {"video": True, "audio": True}})
    prov = {p["name"]: p for p in rec["providers"]}
    g = prov["Google (Gemini)"]["stages"]["screen"]
    assert g["pick"]["model"] == "gemini-b" and g["cheapest"]["model"] == "gemini-a"   # gemini-a rẻ hơn nhưng chưa đạt 90%
    assert prov["Google (Gemini)"]["stages"]["video"]["pick"]["input"] == "video gốc có tiếng"
    assert prov["DeepSeek"]["stages"]["screen"]["why"].startswith("khớp thấp hơn")
    plans = {p["name"] for p in rec["plans"]}
    assert {"Chỉ dùng Anthropic (Claude)", "Chỉ dùng Google (Gemini)", "Chỉ dùng DeepSeek"} <= plans
    assert abs(sum(s["share"] for s in rec["provider_share"]) - 1) < 1e-9
