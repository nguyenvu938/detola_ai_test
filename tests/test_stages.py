"""Test các bước tất định (không gọi API)."""
from koc.sources.kalodata import scrub_pii
from koc.audience import Target, age_overlap
from koc.stages.metrics import compute_metrics, estimate_cost_vnd
from koc.stages.prefilter import percentile_ranks, prefilter
from koc.stages.rationale import check_citations
from koc.stages.select import choose, screen_score

CFG = {
    "prefilter": {"min_followers": 10_000, "max_followers": 500_000,
                  "exclude_name_patterns": ["official", ".vn"], "max_for_enrich": 10},
    "campaign": {"target_gender": "female", "target_age_min": 18, "target_age_max": 30},
    "audience": {"min_target_gender_share": 0.55},
    "weights": {"metric": {"audience": 0.3, "category_gmv": 0.2, "conversion": 0.15,
                           "views_per_follower": 0.15, "engagement": 0.1, "organic": 0.1}},
}
RATE = [{"min_followers": 0, "max_followers": 100_000, "fee_vnd": 2_500_000, "spark_code_vnd": 500_000},
        {"min_followers": 100_000, "max_followers": 10**9, "fee_vnd": 10_000_000}]


def creator(handle, followers=50_000, revenue=100_000_000, nickname=None):
    return {"handle": handle, "nickname": nickname or handle, "followers": followers,
            "revenue_vnd": revenue, "content_views": 1_000_000, "engagement_rate": 0.01, "kalodata_id": "1"}


def test_prefilter_drops_out_of_range_and_brands():
    cs = [creator("a"), creator("big", followers=2_000_000), creator("brand.vn"), creator("x", nickname="X Official")]
    kept, dropped = prefilter(cs, CFG)
    assert [c["handle"] for c in kept] == ["a"]
    assert {d["handle"] for d in dropped} == {"big", "brand.vn", "x"}


def test_prefilter_keeps_unknown_followers_and_rewards_bonus_source():
    cfg = {"prefilter": {**CFG["prefilter"], "bonus_sources": ["creators_list_content"]}}
    a = {**creator("rich"), "sources": ["creators_list"]}
    b = {**creator("reviewer", revenue=0), "followers": None, "sources": ["creators_list_content"]}
    c = {**creator("nosales", revenue=0), "sources": ["creators_list"]}
    kept, dropped = prefilter([a, b, c], cfg)
    assert {k["handle"] for k in kept} == {"rich", "reviewer"}       # chưa biết follower thì giữ lại
    assert [d["handle"] for d in dropped] == ["nosales"]             # không doanh thu, không nguồn ưu tiên


def test_percentile_ranks_handles_none():
    assert percentile_ranks([1, 2, None]) == [0.25, 0.75, 0.5]


def test_target_numeric_share_18_30_female():
    t = Target({"target_gender": "female", "target_age_min": 18, "target_age_max": 30})
    share = t.share_numeric({"female": 0.8}, {"18-24": 0.4, "25-34": 0.5})
    assert abs(share - 0.8 * (0.4 + 0.5 * 0.6)) < 1e-9      # nhóm 25-34 trùng 6/10 năm với 18-30


def test_age_overlap_and_other_brief():
    assert age_overlap("18-24", 18, 30) == 1.0
    assert abs(age_overlap("25_34", 18, 30) - 0.6) < 1e-9
    assert age_overlap("35_plus", 18, 30) == 0
    # Brief khác: nam 25-40 -> nhãn "Majority Male" là đúng, "Majority Female" là lệch
    t = Target({"target_gender": "male", "target_age_min": 25, "target_age_max": 40})
    assert t.is_wrong_majority("Majority Female") and not t.is_wrong_majority("Majority Male")
    assert t.score_from_labels("Majority Male", "25-34") == 1.0
    assert t.describe() == "nam 25–40 tuổi"


def test_metrics_drop_low_female_and_missing_detail():
    cands = [creator("ok"), creator("male"), creator("nodetail")]
    details = {
        "ok": {"follower_gender": {"female": 0.9}, "follower_age": {"18-24": 0.5, "25-34": 0.3},
               "videos": [{"views": 10_000, "is_ad": False}], "followers": 50_000, "creator_type": "INDEPENDENT"},
        "male": {"follower_gender": {"female": 0.3}, "follower_age": {"18-24": 0.5}, "videos": []},
    }
    rows, dropped = compute_metrics(cands, details, CFG, RATE)
    assert [r["handle"] for r in rows] == ["ok"]
    assert {d["handle"] for d in dropped} == {"male", "nodetail"}
    assert 0 <= rows[0]["metric_score"] <= 1


def test_audience_from_coarse_labels_and_male_drop():
    base = {"videos": [{"views": 1000}], "creator_type": "INDEPENDENT", "follower_gender": None, "follower_age": None}
    details = {
        "f": {**base, "follower_sex_label": "Majority Female", "follower_age_top": "18-24"},
        "m": {**base, "follower_sex_label": "Majority Male", "follower_age_top": "18-24"},
        "none": {**base},
    }
    rows, dropped = compute_metrics([creator("f"), creator("m"), creator("none")], details, CFG, RATE)
    by = {r["handle"]: r for r in rows}
    assert by["f"]["audience_score"] == 1.0
    assert by["none"]["audience_score"] is None          # để bước chọn suy từ video
    assert [d["handle"] for d in dropped] == ["m"]


def test_estimate_cost_by_tier():
    assert estimate_cost_vnd(50_000, RATE) == 3_000_000
    assert estimate_cost_vnd(200_000, RATE) == 10_000_000


def test_choose_respects_budget():
    pool = [{"handle": f"k{i}", "final_score": 1 - i * 0.1, "est_cost_vnd": c}
            for i, c in enumerate([20_000_000, 3_000_000, 3_000_000, 3_000_000, 3_000_000, 3_000_000])]
    res = choose(pool, n=5, budget_vnd=30_000_000)
    assert res["total_cost_vnd"] <= 30_000_000
    assert len(res["selected"]) == 5
    # KOC điểm cao nhất nhưng quá đắt (20tr + 4×3tr = 32tr) bị bỏ để vừa ngân sách
    assert "k0" not in {s["handle"] for s in res["selected"]}


def test_screen_score_gates_brand_accounts():
    base = {"topic_relevance": 8, "brand_safety_flags": []}
    assert screen_score({**base, "account_kind": "shop_seller"}) == 0
    assert screen_score({**base, "account_kind": "individual_creator"}) == 0.8
    assert screen_score({**base, "account_kind": "agency_team"}) == 0.4


def test_check_citations_flags_invented_refs():
    packs = [{"handle": "a", "evidence": {"M:gmv": "...", "V:1": "..."}}]
    rat = {"kocs": [{"handle": "a", "evidence_refs": ["M:gmv", "V:999"]}]}
    cc = check_citations(rat, packs)
    assert cc["refs_invalid"] == ["a:V:999"]
    assert cc["valid_rate"] == 0.5
    assert cc["handles_match"]


def test_scrub_pii():
    s = scrub_pii("Booking: 039 6921 840 - mail abc.def@gmail.com")
    assert "039" not in s and "gmail" not in s


def test_reach_flag_uses_tier_benchmark():
    from koc.stages.metrics import reach_flag
    bm = [{"max_followers": 100_000, "min_views_per_follower": 0.2}, {"max_followers": 10**9, "min_views_per_follower": 0.1}]
    assert reach_flag(50_000, 0.05, bm).startswith("view/follower 5%")
    assert reach_flag(50_000, 0.30, bm) is None
    assert reach_flag(300_000, 0.15, bm) is None        # kênh lớn: chuẩn thấp hơn


def test_contact_groups_and_choose_one_per_group():
    from koc.sources.kalodata import contact_groups, contact_keys
    details = {
        "a": {"contact_keys": contact_keys("Booking: 0912 345 678")},
        "b": {"contact_keys": contact_keys("LH quản lý 0912.345.678")},   # cùng số, khác cách viết
        "c": {"contact_keys": contact_keys("mail c@gmail.com")},
    }
    g = contact_groups(details)
    assert g["a"] == g["b"] != g["c"]
    pool = [{"handle": "a", "final_score": 0.9, "est_cost_vnd": 1, "contact_group": g["a"]},
            {"handle": "b", "final_score": 0.8, "est_cost_vnd": 1, "contact_group": g["a"]},
            {"handle": "c", "final_score": 0.5, "est_cost_vnd": 1, "contact_group": None}]
    picked = {s["handle"] for s in choose(pool, n=3, budget_vnd=10)["selected"]}
    assert picked == {"a", "c"}          # không chọn cả a và b; thiếu người thì chọn 2 thay vì 3


def test_revenue_from_other_basis_is_neutral():
    base = {"videos": [{"views": 1000}], "creator_type": "INDEPENDENT", "followers": 50_000}
    cands = [{**creator("cat_low", revenue=1), "revenue_basis": "creators_list"},
             {**creator("cat_high", revenue=10**9), "revenue_basis": "creators_list"},
             {**creator("all_cat", revenue=10**12), "revenue_basis": "creators_list_research"}]
    rows, _ = compute_metrics(cands, {c["handle"]: base for c in cands}, CFG, RATE)
    by = {r["handle"]: r["metric_parts"]["category_gmv"] for r in rows}
    assert by["all_cat"] == 0.5          # doanh thu mọi ngành: không so với doanh thu danh mục
    assert by["cat_high"] > by["cat_low"]


def test_fallback_routing_when_key_missing():
    from koc.config import apply_fallbacks
    cfg = {"models": {"g": {"provider": "gemini"}, "h": {"provider": "anthropic"}},
           "routing": {"video": {"model": "g", "fallback": "h"}, "screen": {"model": "h"}}}
    notes = apply_fallbacks(cfg, {"ANTHROPIC_API_KEY": "x"})
    assert cfg["routing"]["video"]["model"] == "h" and len(notes) == 1
    cfg2 = {"models": cfg["models"], "routing": {"video": {"model": "g", "fallback": "h"}}}
    assert apply_fallbacks(cfg2, {"GEMINI_API_KEY": "y"}) == [] and cfg2["routing"]["video"]["model"] == "g"


def test_sanitize_replaces_contact_hashes_with_opaque_ids(tmp_path, monkeypatch):
    """Snapshot công khai không được giữ mã băm số điện thoại (dò ngược được); 2 kênh chung số vẫn chung mã."""
    import json
    from koc.sources import kalodata
    d = tmp_path / "creators"
    d.mkdir()
    bios = {"a": "Booking 0912 345 678", "b": "LH 0912.345.678", "c": "mail c@gmail.com", "e": "không có liên hệ"}
    for h, bio in bios.items():
        (d / f"{h}.json").write_text(json.dumps({"handle": h, "bio": bio}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(kalodata, "KALO_DIR", tmp_path)
    assert kalodata.sanitize_snapshots() == 4
    out = {h: json.loads((d / f"{h}.json").read_text(encoding="utf-8")) for h in bios}
    assert out["a"]["contact_keys"] == out["b"]["contact_keys"] != out["c"]["contact_keys"]
    assert all(k.startswith("lh-") for o in out.values() for k in o["contact_keys"]) and out["e"]["contact_keys"] == []
    assert "0912" not in out["a"]["bio"] and "@" not in out["c"]["bio"]
    assert kalodata.sanitize_snapshots() == 0                     # chạy lại không đổi gì
