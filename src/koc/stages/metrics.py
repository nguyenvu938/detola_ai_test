"""Stage 3 – điểm định lượng từ dữ liệu Kalodata (0 token).

Mỗi chỉ số được đổi sang thang 0..1 rồi cộng có trọng số (config/campaign.toml [weights.metric]).
"""
from statistics import median

from koc.audience import Target
from koc.stages.prefilter import percentile_ranks

# Danh sách nguồn có cột doanh thu = doanh thu theo DANH MỤC chiến dịch (so sánh được với nhau)
COMPARABLE_BASES = {"creators_list", "creators_list_video"}


def ad_share(videos: list[dict]) -> float | None:
    """Tỷ lệ lượt xem đến từ video có chạy quảng cáo (trả tiền), tính theo view."""
    total = sum(v.get("views") or 0 for v in videos)
    if not total:
        return None
    paid = sum(v.get("views") or 0 for v in videos if v.get("is_ad"))
    return paid / total


def _tier(followers: int, rate_card: list[dict]) -> dict:
    for tier in rate_card:
        if tier["min_followers"] <= followers < tier["max_followers"]:
            return tier
    return rate_card[-1]


def estimate_cost_vnd(followers: int, rate_card: list[dict]) -> int:
    """Chi phí ước tính 1 video = phí review + phí cấp mã Spark Ads, theo tier follower (config/market.toml)."""
    t = _tier(followers, rate_card)
    return t["fee_vnd"] + t.get("spark_code_vnd", 0)


def reach_flag(followers: int, views_per_follower: float | None, benchmarks: list[dict]) -> str | None:
    """Cờ rủi ro khi lượt xem trung vị / follower thấp hơn chuẩn (dấu hiệu follower ảo hoặc kênh hết tương tác)."""
    if views_per_follower is None or not benchmarks:
        return None
    for b in benchmarks:
        if followers < b["max_followers"]:
            if views_per_follower < b["min_views_per_follower"]:
                return f"view/follower {views_per_follower:.0%} < chuẩn {b['min_views_per_follower']:.0%}"
            return None
    return None


def compute_metrics(candidates: list[dict], details: dict, cfg: dict, rate_card: list[dict],
                    reach_benchmarks: list[dict] | None = None):
    """Trả (đạt, bị loại). candidates: dòng từ creators_list; details: handle -> snapshot chi tiết."""
    aud_cfg = cfg["audience"]
    target = Target(cfg["campaign"])
    rows, dropped = [], []
    for c in candidates:
        d = details.get(c["handle"])
        if d is None:
            dropped.append({"handle": c["handle"], "reason": "chưa có dữ liệu chi tiết"})
            continue
        if d.get("creator_type") and d["creator_type"] != "INDEPENDENT":
            dropped.append({"handle": c["handle"], "reason": f"creator_type={d['creator_type']}"})
            continue
        g_share = target.gender_share(d.get("follower_gender"))
        if g_share is not None and g_share < aud_cfg["min_target_gender_share"]:
            dropped.append({"handle": c["handle"],
                            "reason": f"follower đúng giới mục tiêu {g_share:.0%} < {aud_cfg['min_target_gender_share']:.0%}"})
            continue
        if target.is_wrong_majority(d.get("follower_sex_label")):
            dropped.append({"handle": c["handle"], "reason": f"Kalodata: {d.get('follower_sex_label')} (lệch giới mục tiêu)"})
            continue
        # 3 mức dữ liệu khán giả, từ tốt đến kém: số liệu đầy đủ -> nhãn thô -> (ở bước chọn) suy từ video
        t_share = target.share_numeric(d.get("follower_gender"), d.get("follower_age"))
        if t_share is not None:
            aud_score, aud_source = min(1.0, t_share / 0.5), "kalodata: số liệu"
        else:
            aud_score = target.score_from_labels(d.get("follower_sex_label"), d.get("follower_age_top"))
            aud_source = (f"kalodata: nhãn ({d.get('follower_sex_label')}, tuổi {d.get('follower_age_top')})"
                          if aud_score is not None else None)
        videos = d.get("videos") or []
        views = [v["views"] for v in videos if v.get("views")]
        followers = d.get("followers") or c["followers"]
        vpf = (median(views) / followers) if views and followers else None
        rows.append({
            "reach_flag": reach_flag(followers, vpf, reach_benchmarks or []),
            "handle": c["handle"],
            "nickname": c["nickname"],
            "followers": followers,
            "target_gender_share": g_share,
            "target_share": t_share,
            "audience_score": aud_score,     # None = chưa biết, sẽ suy từ video ở bước chọn
            "audience_source": aud_source,
            "category_gmv_vnd": c["revenue_vnd"],
            "gmv_basis": c.get("revenue_basis", "creators_list"),
            "gmv_per_1k_views": (c["revenue_vnd"] / c["content_views"] * 1000) if c.get("content_views") else None,
            "views_per_follower": vpf,
            "engagement_rate": c.get("engagement_rate"),
            "ad_share": ad_share(videos),
            "est_cost_vnd": estimate_cost_vnd(followers, rate_card),
        })

    if not rows:
        return rows, dropped
    # Chỉ so doanh thu giữa những người CÙNG cơ sở (doanh thu theo danh mục chiến dịch). Nguồn khác cơ sở
    # (mọi ngành hàng / chỉ vài video organic) -> None -> trung tính 0.5, tránh thổi phồng hoặc dìm điểm.
    comparable = lambda r: r.get("gmv_basis", "creators_list") in COMPARABLE_BASES  # noqa: E731
    pr = {
        "category_gmv": percentile_ranks([r["category_gmv_vnd"] if comparable(r) else None for r in rows]),
        "conversion": percentile_ranks([r["gmv_per_1k_views"] if comparable(r) else None for r in rows]),
        "views_per_follower": percentile_ranks([r["views_per_follower"] for r in rows]),
        "engagement": percentile_ranks([r["engagement_rate"] for r in rows]),
    }
    w = cfg["weights"]["metric"]
    for i, r in enumerate(rows):
        # Khán giả: thang tuyệt đối (50% follower đúng giới + tuổi mục tiêu coi như tối đa), thiếu dữ liệu -> 0.5 trung tính
        audience = r["audience_score"] if r["audience_score"] is not None else 0.5
        organic = 1 - r["ad_share"] if r["ad_share"] is not None else 0.5
        parts = {
            "audience": audience,
            "category_gmv": pr["category_gmv"][i],
            "conversion": pr["conversion"][i],
            "views_per_follower": pr["views_per_follower"][i],
            "engagement": pr["engagement"][i],
            "organic": organic,
        }
        r["metric_parts"] = {k: round(v, 3) for k, v in parts.items()}
        r["metric_score"] = round(sum(w[k] * parts[k] for k in w), 4)
    rows.sort(key=lambda r: r["metric_score"], reverse=True)
    return rows, dropped
