"""Stage 1 – lọc sơ bộ bằng luật, không tốn token.

Mục tiêu: bỏ càng nhiều ứng viên chắc chắn không hợp càng sớm càng tốt,
để các bước tốn tiền (LLM, video) chỉ chạy trên số ít còn lại.
"""
import math
from bisect import bisect_left, bisect_right


def is_brand_like(creator: dict, patterns: list[str]) -> bool:
    name = f"{creator.get('handle', '')} {creator.get('nickname', '')}".lower()
    return any(p in name for p in patterns)


def percentile_ranks(values: list[float | None]) -> list[float]:
    """Đổi giá trị thô sang hạng phần trăm 0..1 trong nhóm ứng viên (None -> 0.5 trung tính)."""
    known = sorted(v for v in values if v is not None)
    if not known:
        return [0.5] * len(values)
    out = []
    for v in values:
        if v is None:
            out.append(0.5)
            continue
        # tìm nhị phân trên danh sách đã sắp xếp: O(N log N) thay vì đếm lại cả danh sách cho mỗi người (O(N²),
        # 10.000 creator = 100 triệu phép so sánh)
        below = bisect_left(known, v)
        equal = bisect_right(known, v) - below
        out.append((below + 0.5 * equal) / len(known))
    return out


def prefilter(creators: list[dict], cfg: dict) -> tuple[list[dict], list[dict]]:
    """Trả (giữ lại, bị loại kèm lý do). Danh sách giữ lại đã xếp theo điểm sơ bộ giảm dần."""
    pf = cfg["prefilter"]
    bonus_sources = set(pf.get("bonus_sources", []))
    kept, dropped = [], []
    for c in creators:
        reason = None
        followers = c.get("followers")   # danh sách theo video có thể chưa có -> lấy ở bước enrich
        from_bonus = any(s in bonus_sources for s in c.get("sources", []))
        if followers is not None and not (pf["min_followers"] <= followers <= pf["max_followers"]):
            reason = f"followers {followers:,} ngoài khoảng KOC"
        elif is_brand_like(c, pf["exclude_name_patterns"]):
            reason = "tên giống tài khoản thương hiệu/shop"
        elif not c.get("revenue_vnd") and not from_bonus:
            reason = "không có doanh thu ngành hàng"
        if reason:
            dropped.append({"handle": c["handle"], "reason": reason})
        else:
            kept.append(c)

    # Điểm sơ bộ (chỉ dùng dữ liệu có sẵn trong danh sách, chưa tốn gì):
    #   doanh thu ngành (đã chứng minh bán được) + doanh thu/follower (không thiên vị kênh to)
    #   + engagement của video (shop và tài khoản chỉ livestream thường không có số này)
    #   + có mặt trong nguồn ưu tiên (Top Video Creators, creator của video kem chống nắng nhiều view).
    w = pf.get("pre_score_weights", {"gmv": 0.35, "gmv_per_follower": 0.25, "engagement": 0.25, "bonus_source": 0.15})
    gmv = percentile_ranks([math.log1p(c.get("revenue_vnd") or 0) for c in kept])
    per_f = percentile_ranks([(c.get("revenue_vnd") or 0) / c["followers"] if c.get("followers") else None for c in kept])
    # Kalodata ghi "-" (None) khi không tính được engagement: coi là trung tính, KHÔNG phải 0.
    # (Shop / tài khoản chỉ livestream đã có luật khác loại: creator_type, LLM sàng lọc.)
    eng = percentile_ranks([c.get("engagement_rate") for c in kept])
    for c, a, b, e in zip(kept, gmv, per_f, eng):
        bonus = any(s in bonus_sources for s in c.get("sources", []))
        c["pre_score"] = round(w["gmv"] * a + w["gmv_per_follower"] * b + w["engagement"] * e
                               + w["bonus_source"] * bonus, 4)
    kept.sort(key=lambda c: c["pre_score"], reverse=True)
    return kept, dropped


def funnel_caps(camp: dict) -> dict:
    """Số người tối đa ở mỗi tầng phễu tốn tiền, TỶ LỆ với số KOC cần tìm (5 KOC -> 60/40/10; 500 KOC -> 6000/4000/1000).
    Hạn mức theo nguồn (enrich_quota) là tỷ lệ giữa các nguồn, nhân theo số suất lấy chi tiết.
    Config cũ ghi số cố định (max_for_enrich...) vẫn đọc được."""
    n = camp["campaign"]["n_koc"]
    pf, fn = camp["prefilter"], camp["funnel"]
    quota = pf.get("enrich_quota", {})
    if "enrich_per_koc" in pf:
        enrich = pf["enrich_per_koc"] * n
        total_q = sum(quota.values()) or 1
        quota = {k: round(v * enrich / total_q) for k, v in quota.items()}
    else:
        enrich = pf["max_for_enrich"]
    return {
        "enrich": enrich,
        "quota": quota,
        "screen": fn["screen_per_koc"] * n if "screen_per_koc" in fn else fn["max_for_screen"],
        "video": fn["video_per_koc"] * n if "video_per_koc" in fn else fn["max_for_video"],
    }


def shortlist_by_quota(kept: list[dict], quotas: dict[str, int], total: int,
                       rank_by_pre_score: tuple[str, ...] = ("creators_list",)) -> list[dict]:
    """Chọn ai được lấy chi tiết: mỗi nguồn ứng viên lấy theo hạn mức, xếp theo thứ hạng RIÊNG của nguồn đó
    (bảng doanh thu xếp theo doanh thu, nguồn video xếp theo lượt xem organic...). Chỗ còn trống lấy theo pre_score.
    Giống "multi-channel recall" trong hệ gợi ý: một tín hiệu duy nhất sẽ bỏ sót cả một nhóm ứng viên."""
    chosen, seen = [], set()

    def add(c):
        if c["handle"] not in seen and len(chosen) < total:
            seen.add(c["handle"])
            chosen.append(c)

    for source, quota in quotas.items():
        if source in rank_by_pre_score:    # nguồn không có thứ hạng riêng có ý nghĩa -> dùng pre_score
            pool = [c for c in kept if source in c.get("sources", [])]
        else:
            pool = sorted((c for c in kept if source in c.get("sources", [])),
                          key=lambda c: c["source_ranks"].get(source) or 10**9)
        taken = 0
        for c in pool:
            if taken >= quota:
                break
            if c["handle"] not in seen:
                add(c)
                taken += 1
    for c in kept:                          # bù chỗ trống
        add(c)
    return chosen
