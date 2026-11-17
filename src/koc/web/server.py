"""`koc serve` – trang web xem kết quả trên localhost (chỉ đọc).

Dùng http.server có sẵn của Python (không thêm framework). Chỉ lắng nghe 127.0.0.1.
Mọi API đọc thẳng từ results/*.json và state/koc.db mỗi lần gọi, nên chạy pipeline/benchmark
ở cửa sổ khác thì trang tự cập nhật (tab Tiến độ hỏi lại mỗi 2 giây).

  GET /                        giao diện (static/index.html)
  GET /api/runs                các run có trong SQLite + run có kết quả
  GET /api/result?run=ID       results/ID/result.json (rút gọn cho giao diện)
  GET /api/progress?run=ID     tiến độ từng stage, chi phí, lời gọi model gần nhất
  GET /api/benchmark           results/benchmark_models.json
  GET /api/scale               results/scale_test.json (koc scale-test)
  GET /video/<video_id>.mp4    video đã tải ở data/videos (nếu có) – hỗ trợ tua (Range)
"""
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from koc import config
from koc.media import VIDEO_DIR
from koc.store import Store

STATIC = Path(__file__).parent / "static"
RUN_ID_RE = re.compile(r"^[\w.\-]{1,80}$")
VIDEO_ID_RE = re.compile(r"^\d{5,25}$")


# ---------------- dữ liệu cho API (hàm thuần, test được) ----------------
def list_runs(store: Store) -> list[dict]:
    rows = store.db.execute(
        """SELECT r.run_id, r.status, r.started_at, r.finished_at,
                  COALESCE((SELECT SUM(cost_usd) FROM llm_calls c WHERE c.run_id = r.run_id), 0) AS cost_usd
           FROM runs r WHERE r.run_id NOT LIKE 'bench-%' AND r.run_id NOT LIKE 'smoke%'
           ORDER BY r.started_at DESC"""
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["has_result"] = (config.RESULTS_DIR / d["run_id"] / "result.json").exists()
        out.append(d)
    return out


def load_result(run_id: str) -> dict | None:
    p = config.RESULTS_DIR / run_id / "result.json"
    if not p.exists():
        return None
    r = json.loads(p.read_text(encoding="utf-8"))
    final = r.get("final") or {}
    rat = {k["handle"]: k for k in (final.get("rationale") or {}).get("kocs", [])}
    packs = {p_["handle"]: p_["evidence"] for p_ in final.get("packs") or []}
    kocs = []
    for s in r["choice"]["selected"]:
        h = s["handle"]
        v = r["videos"].get(h) or {}
        kocs.append({
            "row": s,
            "screen": r["screens"].get(h),
            "video": {k: v.get(k) for k in ("video_id", "url", "kind", "description", "views", "stats",
                                             "input", "analysis", "format_mix")},
            "has_local_video": bool(v.get("video_id")) and (VIDEO_DIR / v["video_id"] / f"{v['video_id']}.mp4").exists(),
            "rationale": rat.get(h),
            "evidence": packs.get(h, {}),
        })
    return {
        "run_id": r["run_id"],
        "campaign": r.get("campaign"),
        "generated_at": r.get("generated_at"),
        "routing": r.get("routing"),
        "llm_calls": r.get("llm_calls"),
        "registry_changes": r.get("registry_changes") or [],
        "funnel": r["funnel"],
        "summary": (final.get("rationale") or {}).get("summary_vi"),
        "citation_check": final.get("citation_check"),
        "choice": {k: r["choice"].get(k) for k in ("total_cost_vnd", "ads_reserve_vnd", "recommended_ads_vnd",
                                                     "note", "ads_note", "below_threshold")},
        "kocs": kocs,
        "dropped": r["dropped"]["metrics"],
        "screens": [{"handle": h, **{k: s.get(k) for k in ("account_kind", "primary_niche", "topic_relevance", "fit_note")}}
                    for h, s in r["screens"].items()],
        "usage": r["usage"],
        "timings": r["timings"],
        "cost_usd": r["cost_usd"],
    }


def progress(store: Store, run_id: str) -> dict:
    run = store.db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
    stages = {}
    for row in store.db.execute(
        "SELECT stage, status, COUNT(*) n FROM stage_items WHERE run_id=? GROUP BY stage, status", (run_id,)
    ):
        stages.setdefault(row["stage"], {})[row["status"]] = row["n"]
    calls = store.db.execute(
        """SELECT stage, model, cache_hit, ok, input_tokens, output_tokens, cost_usd, latency_ms, created_at
           FROM llm_calls WHERE run_id=? ORDER BY id DESC LIMIT 15""", (run_id,)
    ).fetchall()
    return {
        "run": dict(run) if run else None,
        "now": time.time(),
        "stages": stages,
        "usage": store.usage_by_stage(run_id),
        "timings": store.timings(run_id),
        "cost_usd": store.run_cost(run_id),
        "recent_calls": [dict(c) for c in calls],
    }


def load_benchmark() -> dict | None:
    p = config.RESULTS_DIR / "benchmark_models.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_scale() -> dict | None:
    p = config.RESULTS_DIR / "scale_test.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def export_static(run_id: str = "final", out: Path | None = None) -> Path:
    """Một file HTML tự chứa (dữ liệu nhúng sẵn): bấm đúp là xem, không cần Python, không cần API key."""
    result = load_result(run_id)
    if result is None:
        raise SystemExit(f"Chưa có results/{run_id}/result.json")
    for k in result["kocs"]:
        k["has_local_video"] = False          # bản tĩnh không kèm video -> hiện link TikTok
    data = {"run_id": run_id, "exported_at": time.strftime("%Y-%m-%d %H:%M"),
            "runs": [{"run_id": run_id, "status": "done"}], "results": {run_id: result}, "benchmark": load_benchmark(),
            "scale": load_scale()}
    # "</" trong chuỗi JSON có thể đóng nhầm thẻ <script> -> viết thành "<\/" (JSON vẫn đọc ra "</")
    blob = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    marker = "<script>\n// ---------- tiện ích ----------"
    if marker not in html:
        raise RuntimeError("Không tìm thấy chỗ chèn dữ liệu trong index.html")
    html = html.replace(marker, f"<script>window.__KOC_STATIC__ = {blob};</script>\n{marker}", 1)
    out = out or config.RESULTS_DIR / "report.html"
    out.write_text(html, encoding="utf-8")
    return out


# ---------------- HTTP ----------------
class Handler(BaseHTTPRequestHandler):
    store: Store = None   # gán khi khởi động

    def log_message(self, fmt, *args):   # giữ terminal gọn
        pass

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code=200):
        self._send(code, json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        run = q.get("run", "final")
        if url.path in ("/api/result", "/api/progress") and not RUN_ID_RE.match(run):
            return self._json({"error": "run_id không hợp lệ"}, 400)
        try:
            if url.path == "/":
                return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            if url.path == "/api/runs":
                return self._json(list_runs(self.store))
            if url.path == "/api/result":
                data = load_result(run)
                return self._json(data) if data else self._json({"error": f"chưa có results/{run}/result.json"}, 404)
            if url.path == "/api/progress":
                return self._json(progress(self.store, run))
            if url.path == "/api/benchmark":
                data = load_benchmark()
                return self._json(data) if data else self._json({"error": "chưa có benchmark"}, 404)
            if url.path == "/api/scale":
                data = load_scale()
                return self._json(data) if data else self._json({"error": "chưa có results/scale_test.json"}, 404)
            m = re.match(r"^/video/(\d+)\.mp4$", url.path)
            if m and VIDEO_ID_RE.match(m.group(1)):
                return self._video(VIDEO_DIR / m.group(1) / f"{m.group(1)}.mp4")
            return self._json({"error": "không có"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _video(self, path: Path):
        """Trả mp4 có hỗ trợ Range để trình duyệt tua được tới mốc bằng chứng."""
        if not path.exists():
            return self._json({"error": "video chưa tải về máy này"}, 404)
        size = path.stat().st_size
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and (m := re.match(r"bytes=(\d*)-(\d*)", rng)):
            if m.group(1):
                start = int(m.group(1))
            if m.group(2):
                end = min(int(m.group(2)), size - 1)
        with open(path, "rb") as f:
            f.seek(start)
            body = f.read(end - start + 1)
        if rng:
            self._send(206, body, "video/mp4", {"Content-Range": f"bytes {start}-{end}/{size}", "Accept-Ranges": "bytes"})
        else:
            self._send(200, body, "video/mp4", {"Accept-Ranges": "bytes"})


def serve(port: int = 8000):
    Handler.store = Store(config.STATE_DIR / "koc.db")
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Mở http://127.0.0.1:{port}  (Ctrl+C để dừng)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
