"""Stage 6 – gộp điểm và chọn N KOC trong ngân sách (thuật toán tất định, 0 token).

Vì sao không để LLM chọn: chọn theo điểm + ràng buộc ngân sách là bài toán tối ưu nhỏ,
code làm chính xác, tái lập được, giải thích được từng con số. LLM chỉ viết lời giải thích.
"""
from itertools import combinations

EXCLUDED_KINDS = {"brand_official", "shop_seller"}


def screen_score(s: dict) -> float:
    if s["account_kind"] in EXCLUDED_KINDS:
        return 0.0
    score = s["topic_relevance"] / 10
    if s["account_kind"] == "agency_team":
        score *= 0.5          # team đăng hộ nhiều nhãn: kém "người dùng thật" hơn
    elif s["account_kind"] == "unknown":
        score *= 0.7          # LLM không chắc là người thật -> trừ điểm, không loại hẳn
    score -= 0.15 * len(s.get("brand_safety_flags") or [])
    return max(0.0, min(1.0, score))


def video_score(v: dict) -> float:
    # "Thoa lên da" và "thấy kết cấu" chỉ là bằng chứng khi đúng sản phẩm của chiến dịch:
    # thoa sữa tắm lên da không chứng minh creator review được kem chống nắng.
    on = v["is_on_topic"]
    checks = [on, v["face_on_camera"], on and v["product_demo_on_skin"], on and v["shows_texture_or_finish"]]
    base = (sum(checks) / len(checks)) * 0.6 + (v["hook_strength"] / 5) * 0.2 + (v["production_quality"] / 5) * 0.2
    base -= 0.15 * len(v.get("risky_claims") or [])
    return max(0.0, min(1.0, base))




def combine(metrics: list[dict], screens: dict, videos: dict, weights: dict, audience_weight: float = 0.0,
            photo_post_factor: float = 1.0, target=None) -> list[dict]:
    """Chỉ creator đã qua đủ 3 lớp bằng chứng mới được xét chọn."""
    pool = []
    for m in metrics:
        s, v = screens.get(m["handle"]), videos.get(m["handle"])
        if not s or not v:
            continue
        if s["account_kind"] in EXCLUDED_KINDS:
            continue
        a = v["analysis"]
        metric = m["metric_score"]
        audience_source = m.get("audience_source")
        if m.get("audience_score") is None:
            # thay phần "audience" trung tính 0.5 bằng proxy từ video
            # Giả định (ghi rõ trong báo cáo): người dẫn đúng giới/tuổi mục tiêu thường kéo khán giả tương tự
            proxy = target.score_from_presenter(a["presenter_gender"], a["presenter_age_band"]) if target else 0.5
            metric = metric + audience_weight * (proxy - 0.5)
            audience_source = f"suy từ video ({proxy:.2f})"
        sc, vc = screen_score(s), video_score(a)
        if v.get("kind") != "video":       # chỉ thấy ảnh bìa (+ âm thanh) -> bằng chứng yếu hơn
            vc *= photo_post_factor
        final = weights["metric"] * metric + weights["screen"] * sc + weights["video"] * vc
        pool.append({**m, "metric_score": round(metric, 4), "audience_source": audience_source,
                     "screen_score": round(sc, 3), "video_score": round(vc, 3), "final_score": round(final, 4)})
    pool.sort(key=lambda r: r["final_score"], reverse=True)
    return pool


EXACT_MAX_N = 6   # n nhỏ: vét cạn (chính xác). n lớn: số tổ hợp bùng nổ -> thuật toán gần đúng bên dưới


def choose(pool: list[dict], n: int, budget_vnd: int, top_k: int = 20) -> dict:
    """Chọn n KOC có tổng điểm lớn nhất mà
      - tổng chi phí ước tính <= ngân sách, và
      - không có 2 KOC cùng nhóm liên hệ (chung người quản lý/agency -> độ phủ trùng).
    Không đủ n người hợp lệ thì lấy số người lớn nhất vừa ngân sách."""
    if n <= EXACT_MAX_N:
        return _choose_exact(pool, n, budget_vnd, top_k)
    return _choose_large(pool, n, budget_vnd)


def _result(best: list[dict] | None, budget_vnd: int) -> dict:
    if not best:
        return {"selected": [], "total_cost_vnd": 0, "reserve_vnd": budget_vnd,
                "note": "Không tổ hợp nào vừa ngân sách – cần nới ngân sách hoặc chọn KOC tier nhỏ hơn"}
    total = sum(c["est_cost_vnd"] for c in best)
    return {"selected": sorted(best, key=lambda c: c["final_score"], reverse=True),
            "total_cost_vnd": total, "reserve_vnd": budget_vnd - total, "note": ""}


def _choose_exact(pool: list[dict], n: int, budget_vnd: int, top_k: int) -> dict:
    """Vét cạn tổ hợp trong top_k người điểm cao nhất. C(20,5) = 15.504 tổ hợp: dưới 0,1 giây.
    top_k = 20 (không phải 12) để khi top đầu toàn kênh đắt/cùng nhóm liên hệ vẫn còn kênh rẻ hơn để ghép đủ n người.
    Không đủ n người hợp lệ thì thử n-1, n-2..."""
    cand = pool[:top_k]
    best, best_score = None, -1.0
    for size in range(min(n, len(cand)), 0, -1):
        for combo in combinations(cand, size):
            groups = [c.get("contact_group") for c in combo if c.get("contact_group")]
            if len(groups) != len(set(groups)):
                continue
            cost = sum(c["est_cost_vnd"] for c in combo)
            if cost > budget_vnd:
                continue
            score = sum(c["final_score"] for c in combo)
            if score > best_score:
                best, best_score = combo, score
        if best is not None:
            break
    return _result(list(best) if best else None, budget_vnd)


def _cost(sel: list[dict]) -> int:
    return sum(c["est_cost_vnd"] for c in sel)


def _pick(pool: list[dict], n: int, lam: float) -> list[dict]:
    """n người có (điểm − lam × chi phí) cao nhất, tối đa 1 người mỗi nhóm liên hệ.
    lam = "giá" của 1 đồng: lam = 0 chọn theo điểm thuần; lam lớn thì ưu tiên người rẻ."""
    out, used = [], set()
    for c in sorted(pool, key=lambda c: c["final_score"] - lam * c["est_cost_vnd"], reverse=True):
        g = c.get("contact_group")
        if g and g in used:
            continue
        if g:
            used.add(g)
        out.append(c)
        if len(out) == n:
            break
    return out


def _choose_large(pool: list[dict], n: int, budget_vnd: int) -> dict:
    """Bài toán chọn n người trong ngân sách (knapsack có giới hạn số lượng) cho n lớn, 50–500 KOC.

    1. Cỡ bộ: n, hoặc số người lớn nhất mà bộ RẺ NHẤT cỡ đó vừa ngân sách (tìm nhị phân).
    2. Nhân tử Lagrange: tìm "giá mỗi đồng" lam nhỏ nhất mà bộ n người có (điểm − lam × chi phí) cao nhất
       vừa ngân sách (tìm nhị phân trên lam, mỗi lần chỉ là 1 lần sắp xếp).
    3. Đổi chỗ: còn dư ngân sách thì thay người điểm thấp bằng người ngoài điểm cao hơn, đến khi hết cách cải thiện.
    Chạy O(N log N) mỗi vòng, vài giây với hàng nghìn ứng viên; test so với vét cạn ở cỡ nhỏ."""
    if not pool:
        return _result(None, budget_vnd)
    lam_hi = 1e-3          # điểm chênh tối đa 1, chi phí chênh tối thiểu ~250k VNĐ -> lam này chỉ còn xét chi phí
    lo, hi = 0, min(n, len(pool))
    while lo < hi:         # bước 1: cỡ bộ lớn nhất còn vừa ngân sách
        mid = (lo + hi + 1) // 2
        if _cost(_pick(pool, mid, lam_hi)) <= budget_vnd:
            lo = mid
        else:
            hi = mid - 1
    size = lo
    if size == 0:
        return _result(None, budget_vnd)
    best = _pick(pool, size, 0.0)
    if _cost(best) > budget_vnd:   # bước 2
        a, b = 0.0, lam_hi
        best = _pick(pool, size, b)
        for _ in range(40):
            mid = (a + b) / 2
            sel = _pick(pool, size, mid)
            if _cost(sel) <= budget_vnd:
                b, best = mid, sel
            else:
                a = mid
    return _result(_improve(pool, best, budget_vnd), budget_vnd)


def _improve(pool: list[dict], sel: list[dict], budget_vnd: int) -> list[dict]:
    """Bước 3 – đổi 1 người trong bộ lấy 1 người ngoài nếu tổng điểm tăng mà vẫn vừa ngân sách.
    Chỉ cần xét người điểm THẤP NHẤT trong bộ và người điểm CAO NHẤT ngoài bộ ở từng mức chi phí
    (chi phí theo tier nên chỉ có vài mức) -> mỗi vòng nhanh dù có hàng nghìn ứng viên.
    Người ngoài thuộc nhóm liên hệ đã có trong bộ chỉ được đổi với chính người cùng nhóm đó
    (đổi 1 lấy 1 trong cùng nhóm vẫn giữ luật tối đa 1 kênh/nhóm)."""
    sel = list(sel)
    for _ in range(2 * len(sel)):
        chosen = {c["handle"] for c in sel}
        used_groups = {c["contact_group"] for c in sel if c.get("contact_group")}
        left = budget_vnd - _cost(sel)
        worst_in, best_out, best_same = {}, {}, {}
        for c in sel:
            k = c["est_cost_vnd"]
            if k not in worst_in or c["final_score"] < worst_in[k]["final_score"]:
                worst_in[k] = c
        for c in pool:
            if c["handle"] in chosen:
                continue
            g, k = c.get("contact_group"), c["est_cost_vnd"]
            best = best_same if g in used_groups else best_out
            key = (g, k) if g in used_groups else k
            if key not in best or c["final_score"] > best[key]["final_score"]:
                best[key] = c
        pairs = [(o, i) for o in worst_in.values() for i in best_out.values()]
        pairs += [(o, i) for (g, _k), i in best_same.items() for o in sel if o.get("contact_group") == g]
        swap, gain = None, 1e-9
        for o, i in pairs:
            if i["est_cost_vnd"] - o["est_cost_vnd"] <= left and i["final_score"] - o["final_score"] > gain:
                swap, gain = (o, i), i["final_score"] - o["final_score"]
        if swap is None:
            break
        sel = [swap[1] if c is swap[0] else c for c in sel]
    return sel
