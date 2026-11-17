"""Kho trạng thái SQLite: checkpoint từng item, cache kết quả LLM, sổ ghi chi phí.

Vì sao SQLite: 1 file, có transaction (ghi xong mới tính là xong), không cần dựng server.
Mỗi item ghi xong là commit ngay, nên process bị kill giữa chừng thì chạy lại chỉ làm
những item chưa xong.
"""
import functools
import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path


def _locked(fn):
    """Các luồng phân tích video chạy song song dùng chung 1 kết nối SQLite -> khóa từng thao tác."""
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        with self.lock:
            return fn(self, *args, **kwargs)
    return wrapper


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    config_json TEXT,
    started_at REAL,
    finished_at REAL,
    status TEXT
);
CREATE TABLE IF NOT EXISTS stage_items (
    run_id TEXT, stage TEXT, item_id TEXT,
    status TEXT,              -- done | failed | skipped
    output_json TEXT,
    error TEXT,
    attempts INTEGER DEFAULT 0,
    updated_at REAL,
    PRIMARY KEY (run_id, stage, item_id)
);
CREATE TABLE IF NOT EXISTS stage_timing (
    run_id TEXT, stage TEXT, seconds REAL, items INTEGER, updated_at REAL,
    PRIMARY KEY (run_id, stage)
);
CREATE TABLE IF NOT EXISTS llm_cache (
    key TEXT PRIMARY KEY, value_json TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT, stage TEXT, model TEXT, item_ids TEXT,
    input_tokens INTEGER, output_tokens INTEGER,
    cost_usd REAL, latency_ms INTEGER, cache_hit INTEGER, ok INTEGER,
    created_at REAL
);
"""


def cache_key(*parts) -> str:
    raw = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        # WAL + synchronous=NORMAL: mỗi commit không phải chờ ghi đĩa (đo trên máy này: 103 ms -> 0,2 ms/commit;
        # 500 KOC ~17.000 commit ≈ 30 phút -> vài giây). Commit vẫn bền khi process bị kill (điều resume cần);
        # chỉ mất điện mới có thể mất vài commit cuối -> các item đó được làm lại. Trang web đọc song song không bị khóa.
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(llm_calls)")}
        if "saved_usd" not in cols:       # nâng cấp DB cũ, không mất dữ liệu
            self.db.execute("ALTER TABLE llm_calls ADD COLUMN saved_usd REAL DEFAULT 0")
            self.db.commit()

    # ---- runs ----
    @_locked
    def start_run(self, run_id: str, config: dict) -> bool:
        """Tạo run mới hoặc mở lại run cũ. Trả True nếu là resume."""
        row = self.db.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row:
            self.db.execute("UPDATE runs SET status='running' WHERE run_id=?", (run_id,))
            self.db.commit()
            return True
        self.db.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?)",
            (run_id, json.dumps(config, ensure_ascii=False, default=str), time.time(), None, "running"),
        )
        self.db.commit()
        return False

    @_locked
    def finish_run(self, run_id: str):
        self.db.execute("UPDATE runs SET status='done', finished_at=? WHERE run_id=?", (time.time(), run_id))
        self.db.commit()

    # ---- checkpoint từng item ----
    @_locked
    def get_item(self, run_id: str, stage: str, item_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM stage_items WHERE run_id=? AND stage=? AND item_id=?", (run_id, stage, item_id)
        ).fetchone()
        return dict(row) if row else None

    @_locked
    def done_output(self, run_id: str, stage: str, item_id: str):
        row = self.get_item(run_id, stage, item_id)
        if row and row["status"] in ("done", "skipped"):
            return json.loads(row["output_json"]) if row["output_json"] else None, True
        return None, False

    @_locked
    def save_item(self, run_id: str, stage: str, item_id: str, status: str, output=None, error: str | None = None):
        prev = self.get_item(run_id, stage, item_id)
        attempts = (prev["attempts"] if prev else 0) + 1
        self.db.execute(
            "INSERT OR REPLACE INTO stage_items VALUES (?,?,?,?,?,?,?,?)",
            (run_id, stage, item_id, status,
             json.dumps(output, ensure_ascii=False) if output is not None else None,
             error, attempts, time.time()),
        )
        self.db.commit()   # commit từng item = điểm khôi phục

    @_locked
    def reset_stage(self, run_id: str, stage: str) -> int:
        cur = self.db.execute("DELETE FROM stage_items WHERE run_id=? AND stage=?", (run_id, stage))
        self.db.commit()
        return cur.rowcount

    @_locked
    def stage_outputs(self, run_id: str, stage: str) -> dict:
        rows = self.db.execute(
            "SELECT item_id, output_json FROM stage_items WHERE run_id=? AND stage=? AND status='done'",
            (run_id, stage),
        ).fetchall()
        return {r["item_id"]: json.loads(r["output_json"]) for r in rows}

    @_locked
    def add_timing(self, run_id: str, stage: str, seconds: float, items: int):
        """Cộng dồn thời gian xử lý (qua nhiều lần resume)."""
        row = self.db.execute("SELECT seconds FROM stage_timing WHERE run_id=? AND stage=?", (run_id, stage)).fetchone()
        total = (row["seconds"] if row else 0) + seconds
        self.db.execute("INSERT OR REPLACE INTO stage_timing VALUES (?,?,?,?,?)",
                        (run_id, stage, total, items, time.time()))
        self.db.commit()

    # ---- cache LLM ----
    @_locked
    def cache_get(self, key: str):
        row = self.db.execute("SELECT value_json FROM llm_cache WHERE key=?", (key,)).fetchone()
        return json.loads(row["value_json"]) if row else None

    @_locked
    def cache_put(self, key: str, value):
        self.db.execute("INSERT OR REPLACE INTO llm_cache VALUES (?,?,?)",
                        (key, json.dumps(value, ensure_ascii=False), time.time()))
        self.db.commit()

    # ---- sổ chi phí ----
    @_locked
    def log_call(self, run_id, stage, model, item_ids, input_tokens, output_tokens, cost_usd, latency_ms, cache_hit, ok,
                 saved_usd: float = 0.0):
        self.db.execute(
            "INSERT INTO llm_calls (run_id, stage, model, item_ids, input_tokens, output_tokens, cost_usd,"
            " latency_ms, cache_hit, ok, created_at, saved_usd) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, stage, model, json.dumps(item_ids), input_tokens, output_tokens, cost_usd,
             latency_ms, int(cache_hit), int(ok), time.time(), saved_usd),
        )
        self.db.commit()

    @_locked
    def run_cost(self, run_id: str) -> float:
        row = self.db.execute("SELECT COALESCE(SUM(cost_usd),0) c FROM llm_calls WHERE run_id=?", (run_id,)).fetchone()
        return row["c"]

    @_locked
    def usage_by_stage(self, run_id: str) -> list[dict]:
        rows = self.db.execute(
            """SELECT stage, model, COUNT(*) calls, SUM(cache_hit) cache_hits,
                      SUM(input_tokens) input_tokens, SUM(output_tokens) output_tokens,
                      ROUND(SUM(cost_usd), 6) cost_usd, ROUND(AVG(latency_ms)) avg_latency_ms,
                      ROUND(SUM(COALESCE(saved_usd, 0)), 6) saved_usd
               FROM llm_calls WHERE run_id=? GROUP BY stage, model ORDER BY MIN(id)""",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @_locked
    def timings(self, run_id: str) -> list[dict]:
        rows = self.db.execute("SELECT stage, seconds, items FROM stage_timing WHERE run_id=?", (run_id,)).fetchall()
        return [dict(r) for r in rows]
