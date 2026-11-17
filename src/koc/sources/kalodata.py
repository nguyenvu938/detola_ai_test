"""Nguồn dữ liệu Kalodata.

Prototype đọc snapshot JSON (thu thập qua giao diện Kalodata, xem data/kalodata/README.md).
Bản production thay lớp này bằng Kalodata Open API, giữ nguyên các hàm trả về,
nên các stage phía sau không phải sửa.
"""
import hashlib
import json
import re
from pathlib import Path

from koc.config import DATA_DIR

KALO_DIR = DATA_DIR / "kalodata"

# Mỗi danh sách nguồn có cột doanh thu với Ý NGHĨA KHÁC NHAU -> ghi rõ để không so lệch cơ sở
REVENUE_BASIS = {
    "creators_list": "danh mục {product}, mọi kênh bán",
    "creators_list_video": "danh mục {product}, bán qua video",
    "creators_list_content": "từ các video {product} organic trong bảng xếp hạng",
    "creators_list_research": "mọi ngành hàng",
}

# Số VN: bắt đầu 0 hoặc +84, rồi 8–10 chữ số, cho phép dấu cách/chấm/gạch giữa các số (039 6921 840, 0379.757.094)
_PHONE = re.compile(r"(?:\+?84|0)(?:[\s.\-]?\d){8,10}")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def contact_keys(text: str | None) -> list[str]:
    """Mã băm của số điện thoại / email trong bio (không lưu số thật).
    Hai kênh có chung mã = chung người quản lý / agency -> dùng để tránh chọn trùng nhóm."""
    if not text:
        return []
    phones = {re.sub(r"\D", "", m)[-9:] for m in _PHONE.findall(text)}
    emails = {m.lower() for m in _EMAIL.findall(text)}
    return sorted(hashlib.sha256(x.encode()).hexdigest()[:12] for x in phones | emails)


def scrub_pii(text: str | None) -> str:
    """Bỏ số điện thoại và email trong bio trước khi gửi cho LLM hay ghi ra báo cáo."""
    if not text:
        return ""
    text = _EMAIL.sub("[email]", text)
    return _PHONE.sub("[phone]", text)


def load_creator_list(paths: list[Path] | None = None) -> dict:
    """Gộp các danh sách nguồn (creators_list*.json), bỏ trùng theo handle.
    Mỗi creator ghi lại đến từ danh sách nào (để báo cáo phễu theo nguồn)."""
    paths = paths or sorted(KALO_DIR.glob("creators_list*.json"))
    merged: dict[str, dict] = {}
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        for c in data["creators"]:
            if c["handle"] in merged:
                merged[c["handle"]]["sources"].append(p.stem)
                merged[c["handle"]]["source_ranks"][p.stem] = c.get("rank")
            else:
                # số liệu lấy từ file ĐẦU TIÊN chứa creator -> cơ sở doanh thu là của file đó
                merged[c["handle"]] = {**c, "sources": [p.stem], "source_ranks": {p.stem: c.get("rank")},
                                       "revenue_basis": p.stem}
    return {"creators": list(merged.values()), "files": [p.name for p in paths]}


OPAQUE_KEY = re.compile(r"^lh-\d+$")


def sanitize_snapshots() -> int:
    """Ghi đè snapshot chi tiết trước khi đưa repo lên GitHub, để không công khai thông tin liên hệ của creator:
      1. xoá số điện thoại/email khỏi bio;
      2. thay mã băm liên hệ bằng mã VÔ NGHĨA dùng chung cho mọi file ("lh-1", "lh-2"...).
    Vì sao không giữ mã băm: số điện thoại VN chỉ ~1 tỷ khả năng, thử hết mọi số rồi so mã băm là dò ra số thật
    trong vài phút. Bước chọn chỉ cần biết 2 kênh có CHUNG mã hay không, nên mã vô nghĩa là đủ.
    Chạy lại nhiều lần vẫn cho cùng kết quả (mã "lh-" đã có được giữ nguyên). Trả số file đã ghi lại."""
    docs = [(p, json.loads(p.read_text(encoding="utf-8"))) for p in sorted((KALO_DIR / "creators").glob("*.json"))]
    tokens = {k: k for _, d in docs for k in d.get("contact_keys") or [] if OPAQUE_KEY.match(k)}
    next_id = max([int(k[3:]) for k in tokens] or [0]) + 1
    n = 0
    for p, d in docs:
        keys = d["contact_keys"] if "contact_keys" in d else contact_keys(d.get("bio"))   # tính trước khi xoá số
        for k in keys:
            if k not in tokens:
                tokens[k], next_id = f"lh-{next_id}", next_id + 1
        d["contact_keys"] = sorted({tokens[k] for k in keys})
        d["bio"] = scrub_pii(d.get("bio"))
        text = json.dumps(d, ensure_ascii=False, indent=2)
        if text != p.read_text(encoding="utf-8"):
            p.write_text(text, encoding="utf-8")
            n += 1
    return n


def detail_path(handle: str) -> Path:
    return KALO_DIR / "creators" / f"{handle}.json"


def load_creator_detail(handle: str) -> dict | None:
    """Trả None nếu chưa có snapshot (production: gọi API ở đây)."""
    p = detail_path(handle)
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if "contact_keys" not in d:                       # file đã sanitize thì có sẵn mã liên hệ vô nghĩa
        d["contact_keys"] = contact_keys(d.get("bio"))   # tính trước khi xoá số điện thoại/email
    d["bio"] = scrub_pii(d.get("bio"))
    # Trang chi tiết chỉ có 10 video DOANH THU cao nhất; video organic đúng chủ đề (lý do creator vào danh sách
    # theo nội dung) thường không nằm trong đó -> gộp thêm vào, bỏ trùng theo video_id.
    have = {v["video_id"] for v in d.get("videos") or []}
    extra = [v for v in _topic_videos().get(handle, []) if v["video_id"] not in have]
    d["videos"] = (d.get("videos") or []) + extra
    return d


_TOPIC_VIDEOS: dict | None = None


def _topic_videos() -> dict[str, list[dict]]:
    """handle -> các video trong videos_sunscreen.json (bảng xếp hạng video organic theo danh mục)."""
    global _TOPIC_VIDEOS
    if _TOPIC_VIDEOS is None:
        _TOPIC_VIDEOS = {}
        p = KALO_DIR / "videos_sunscreen.json"
        if p.exists():
            for v in json.loads(p.read_text(encoding="utf-8"))["videos"]:
                if v.get("video_id") and v.get("creator_handle"):
                    _TOPIC_VIDEOS.setdefault(v["creator_handle"], []).append({
                        "video_id": v["video_id"], "url": v["url"], "description": v.get("description"),
                        "duration_s": v.get("duration_s"), "views": v.get("views"), "revenue_vnd": v.get("revenue_vnd"),
                        "is_ad": v.get("is_ad"), "publish_date": v.get("publish_date"), "source": "video_rank_organic",
                    })
    return _TOPIC_VIDEOS


def contact_groups(details: dict[str, dict]) -> dict[str, str]:
    """Gom các kênh dùng chung liên hệ thành nhóm (union-find đơn giản). Trả handle -> mã nhóm."""
    parent = {h: h for h in details}

    def find(h):
        while parent[h] != h:
            parent[h] = parent[parent[h]]
            h = parent[h]
        return h

    owner: dict[str, str] = {}
    for h, d in details.items():
        for k in d.get("contact_keys") or []:
            if k in owner:
                parent[find(h)] = find(owner[k])
            else:
                owner[k] = h
    return {h: find(h) for h in details}
