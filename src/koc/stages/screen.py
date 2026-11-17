"""Stage 4 – LLM sàng lọc từ text, gom nhiều creator vào 1 lần gọi.

Tiết kiệm token: chỉ gửi dữ liệu đã rút gọn (bio, 12 tiêu đề video cắt 100 ký tự, tên shop),
prompt hệ thống dùng chung nằm trong cache, 8 creator/lần gọi thay vì 8 lần gọi.
"""
import json

from koc.config import load_prompt, prompt_vars
from koc.llm.base import ADAPTER_VERSION
from koc.registry import follower_bucket
from koc.schemas import ScreenBatch
from koc.store import cache_key

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


def _item_key(llm, route: dict, system: str, profile: dict) -> str:
    """Khoá cache của MỘT creator: model + effort + prompt + hồ sơ rút gọn của chính người đó."""
    provider = llm.models[route["model"]]["provider"]
    return cache_key("screen-item", route["model"], route.get("effort"), system, profile,
                     ScreenBatch.model_json_schema(), ADAPTER_VERSION.get(provider), llm.cache_namespace)


def screen_batch(llm, handles: list[str], details: dict, route: dict, campaign: dict) -> dict[str, dict]:
    """Cache 2 lớp:
    - theo TỪNG creator: lần quét sau có người mới chen vào làm lô 8 người lệch đi thì người cũ vẫn dùng lại được,
      chỉ người chưa có kết quả mới được gửi cho model;
    - theo cả lô (trong LLM.call): giữ được kết quả của các lần chạy trước khi có cache từng creator."""
    system = load_prompt(PROMPT_FILE, **prompt_vars(campaign))
    profiles = {h: compact_profile(h, details[h]) for h in handles}
    keys = {h: _item_key(llm, route, system, profiles[h]) for h in handles}
    out, saved = {}, 0.0
    for h in handles:
        hit = llm.store.cache_get(keys[h]) if llm.use_cache else None
        if hit is not None:
            out[h], saved = hit["__data__"], saved + hit.get("__cost__", 0.0)
    if out:
        llm.store.log_call(llm.run_id, "screen", route["model"], list(out), 0, 0, 0.0, 0, cache_hit=True, ok=True,
                           saved_usd=saved)
    todo = [h for h in handles if h not in out]
    if not todo:
        return out
    res = llm.call(
        stage="screen",
        model=route["model"],
        effort=route.get("effort"),
        system=system,
        parts=[{"type": "text", "text": json.dumps([profiles[h] for h in todo], ensure_ascii=False)}],
        schema=ScreenBatch,
        item_ids=todo,
        max_tokens=6000,
    )
    got = {c["handle"]: c for c in res.data["creators"]}
    missing = [h for h in todo if h not in got]
    if missing:
        raise RuntimeError(f"Model bỏ sót {missing}")
    per_item = (res.usage.cost_usd or res.saved_usd) / len(todo)
    for h in todo:
        llm.store.cache_put(keys[h], {"__data__": got[h], "__cost__": per_item})
        out[h] = got[h]
    return out
