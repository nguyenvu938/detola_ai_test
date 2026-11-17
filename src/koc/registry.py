"""Sổ đăng ký creator: nhớ mỗi creator đã thấy ra sao ở lần quét trước để biết ai MỚI, ai THAY ĐỔI, ai QUÁ HẠN.

"Dấu vân tay" chỉ gồm những thứ làm thay đổi kết luận của AI:
  - danh sách video (có video mới -> có nội dung mới để xem)
  - bio, loại tài khoản, MCN, các shop đang bán (đổi -> phân loại tài khoản / ngách có thể đổi)
  - nhãn khán giả (giới đa số, nhóm tuổi đông nhất)
  - follower làm tròn theo bậc (đổi tier giá booking), KHÔNG dùng số chính xác (đổi hằng ngày)
Lượt xem, like, doanh thu thay đổi mỗi ngày nhưng không làm AI nhìn video khác đi -> không nằm trong vân tay.
"""
import hashlib
import json
import math
import time

STATUS_NEW, STATUS_CHANGED, STATUS_UNCHANGED, STATUS_STALE = "new", "changed", "unchanged", "stale"


def _fmt(x: float) -> str:
    return f"{x / 1e6:.1f}m" if x >= 1e6 else f"{x / 1e3:.0f}k"


def follower_bucket(n: int | None) -> str | None:
    """Bậc follower rộng 25% (cận dưới nhân 1,25 mỗi bậc): 64.200 và 64.900 cùng bậc '57k–71k'.
    Chỉ đổi bậc khi follower thay đổi đáng kể, dao động hằng ngày không làm 'creator thay đổi'."""
    if not n:
        return None
    k = math.floor(math.log(n, 1.25))
    lo = 1.25 ** k
    return f"{_fmt(lo)}–{_fmt(lo * 1.25)}"


def _h(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:10]


def fingerprint(detail: dict) -> dict:
    return {
        "video_ids": sorted(v["video_id"] for v in detail.get("videos") or [] if v.get("video_id")),
        "bio": _h(detail.get("bio")),
        "creator_type": detail.get("creator_type"),
        "mcn": detail.get("mcn_name"),
        "shops": sorted(s["name"] for s in detail.get("shops") or [] if s.get("name")),
        "audience": [detail.get("follower_sex_label"), detail.get("follower_age_top")],
        "followers": follower_bucket(detail.get("followers")),
    }


def diff(old: dict, new: dict) -> list[str]:
    """Mô tả thay đổi bằng lời, để báo cáo và để quyết định bước nào cần làm lại."""
    out = []
    added = sorted(set(new["video_ids"]) - set(old.get("video_ids", [])))
    if added:
        out.append(f"{len(added)} video mới")
    labels = {"bio": "bio", "creator_type": "loại tài khoản", "mcn": "MCN", "audience": "nhãn khán giả",
              "followers": "bậc follower"}
    for k, label in labels.items():
        if old.get(k) != new.get(k):
            out.append(f"{label}: {old.get(k)} -> {new.get(k)}" if k in ("followers", "creator_type", "audience") else label)
    if set(new["shops"]) != set(old.get("shops", [])):
        out.append("shop đang bán thay đổi")
    return out


class Registry:
    """Bảng creator_registry trong cùng file SQLite với checkpoint (state/koc.db)."""

    SCHEMA = """CREATE TABLE IF NOT EXISTS creator_registry (
        handle TEXT PRIMARY KEY, fingerprint_json TEXT, fp_hash TEXT,
        first_seen REAL, last_seen REAL, last_changed REAL, last_changes TEXT)"""

    def __init__(self, store, max_age_days: float = 14):
        self.store = store
        self.max_age = max_age_days * 86400
        with store.lock:
            store.db.execute(self.SCHEMA)
            store.db.commit()

    def observe(self, handle: str, detail: dict, now: float | None = None) -> dict:
        """So vân tay mới với lần trước, cập nhật sổ, trả {status, changes}."""
        now = now or time.time()
        fp = fingerprint(detail)
        fp_hash = _h(json.dumps(fp, sort_keys=True))
        with self.store.lock:
            row = self.store.db.execute("SELECT * FROM creator_registry WHERE handle=?", (handle,)).fetchone()
            if row is None:
                status, changes = STATUS_NEW, ["lần đầu thấy"]
                self.store.db.execute("INSERT INTO creator_registry VALUES (?,?,?,?,?,?,?)",
                                      (handle, json.dumps(fp, ensure_ascii=False), fp_hash, now, now, now,
                                       json.dumps(changes, ensure_ascii=False)))
            elif row["fp_hash"] != fp_hash:
                status, changes = STATUS_CHANGED, diff(json.loads(row["fingerprint_json"]), fp)
                self.store.db.execute(
                    "UPDATE creator_registry SET fingerprint_json=?, fp_hash=?, last_seen=?, last_changed=?, last_changes=? "
                    "WHERE handle=?", (json.dumps(fp, ensure_ascii=False), fp_hash, now, now,
                                       json.dumps(changes, ensure_ascii=False), handle))
            else:
                stale = now - row["last_changed"] > self.max_age
                status = STATUS_STALE if stale else STATUS_UNCHANGED
                changes = [f"quá {self.max_age / 86400:.0f} ngày chưa có thay đổi – nên lấy lại dữ liệu"] if stale else []
                self.store.db.execute("UPDATE creator_registry SET last_seen=? WHERE handle=?", (now, handle))
            self.store.db.commit()
        return {"handle": handle, "status": status, "changes": changes}

    def all(self) -> list[dict]:
        with self.store.lock:
            rows = self.store.db.execute("SELECT * FROM creator_registry ORDER BY last_changed DESC").fetchall()
        return [dict(r) for r in rows]
