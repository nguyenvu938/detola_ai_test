"""Stage 4 – LLM sàng lọc từ text, gom nhiều creator vào 1 lần gọi.

Tiết kiệm token: chỉ gửi dữ liệu đã rút gọn (bio, 10 tiêu đề video cắt 100 ký tự, tên shop),
prompt hệ thống dùng chung nằm trong cache, 8 creator/lần gọi thay vì 8 lần gọi.
"""
import json

from koc.config import load_prompt, prompt_vars
from koc.registry import follower_bucket
from koc.schemas import ScreenBatch

PROMPT_FILE = "screen_v4.txt"   # v1 shop_seller mơ hồ; v2 viết cứng brief; v3 brief từ config;
                                # v4 thang liên quan = mức phù hợp (không chỉ tỷ lệ bài đúng chủ đề), mặc định cá nhân khi INDEPENDENT


def compact_profile(handle: str, detail: dict) -> dict:
    """Thu gọn hồ sơ: chỉ giữ thứ giúp phân loại, cắt chuỗi dài.
    Đưa kèm dữ liệu chắc chắn từ Kalodata (creator_type, tỷ lệ doanh thu live/video) để model không phải đoán."""
    cm = detail.get("core_metrics") or {}
    rev = cm.get("revenue_vnd") or 0
    # làm tròn 0.1: tỷ lệ doanh thu đổi chút ít mỗi ngày không được làm đổi input (-> dùng lại kết quả cũ)
    share = lambda k: round(cm[k] / rev, 1) if rev and cm.get(k) is not None else None  # noqa: E731
    return {
        "handle": handle,
        "nickname": detail.get("nickname"),
        "kalodata_creator_type": detail.get("creator_type"),
        "revenue_share_live": share("live_revenue_vnd"),
        "revenue_share_video": share("video_revenue_vnd"),
        "bio": (detail.get("bio") or "")[:200],
        "mcn": detail.get("mcn_name"),
        "followers": follower_bucket(detail.get("followers")),   # bậc, không phải số chính xác
        # 10 video doanh thu cao nhất + video đúng chủ đề lấy từ bảng xếp hạng danh mục (nếu có)
        "video_titles": [(v.get("description") or "")[:100] for v in (detail.get("videos") or [])[:12]],
        "shops": [s["name"] for s in (detail.get("shops") or [])[:8]],
        "top_products": [(p.get("title") or "")[:80] for p in (detail.get("products") or [])[:5]],
    }


def screen_batch(llm, handles: list[str], details: dict, route: dict, campaign: dict) -> dict[str, dict]:
    profiles = [compact_profile(h, details[h]) for h in handles]
    res = llm.call(
        stage="screen",
        model=route["model"],
        effort=route.get("effort"),
        system=load_prompt(PROMPT_FILE, **prompt_vars(campaign)),
        parts=[{"type": "text", "text": json.dumps(profiles, ensure_ascii=False)}],
        schema=ScreenBatch,
        item_ids=handles,
        max_tokens=6000,
    )
    out = {c["handle"]: c for c in res.data["creators"]}
    missing = [h for h in handles if h not in out]
    if missing:
        raise RuntimeError(f"Model bỏ sót {missing}")
    return out
