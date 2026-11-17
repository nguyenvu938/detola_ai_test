"""Dòng lệnh.

  koc run                    chạy (hoặc tiếp tục) pipeline với cấu hình hiện tại
  koc run --crash-after 3    giả lập sự cố sau 3 lần gọi model, để thử resume
  koc run --video-model claude-sonnet-5-5   đổi model 1 bước mà không sửa file cấu hình
  koc status                 xem tiến độ và chi phí của run
  koc shortlist              in danh sách creator cần lấy chi tiết Kalodata
  koc fetch-videos           tải mp4 từ link Kalodata (data/kalodata/video_urls.json)
  koc changes                ai mới / thay đổi / quá hạn so với các lần quét trước
  koc serve                  mở trang web xem kết quả ở http://127.0.0.1:8000
  koc export-html            ghi results/report.html: 1 file tự chứa, bấm đúp là xem (không cần Python/API key)
  koc scale-test             đo khả năng mở rộng 5/50/500 KOC trên dữ liệu giả lập, model giả (0 đồng)
"""
import argparse
import os
import sys
import time

from dotenv import find_dotenv, load_dotenv

from koc import config, pipeline, report
from koc.llm.base import LLM, BudgetExceeded, SimulatedCrash
from koc.store import Store


def _setup():
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(find_dotenv(usecwd=True))   # tìm .env từ thư mục hiện tại đi lên


def _cfg_with_overrides(args) -> dict:
    cfg = config.load_all()
    routing = cfg["models"]["routing"]
    for stage in ("screen", "video", "rationale"):
        m = getattr(args, f"{stage}_model", None)
        if m:
            routing[stage]["model"] = m
            routing[stage].pop("fallback", None)      # người dùng chọn model cụ thể -> không tự đổi
    for note in config.apply_fallbacks(cfg["models"], os.environ):
        print("Định tuyến dự phòng:", note)
    return cfg


def _run_id(cfg: dict, override: str | None) -> str:
    if override:
        return override
    key = {"campaign": cfg["campaign"], "routing": cfg["models"]["routing"]}
    return f"{cfg['campaign']['campaign']['name']}-{config.config_hash(key)}"


def cmd_run(args):
    cfg = _cfg_with_overrides(args)
    run_id = _run_id(cfg, args.run_id)
    store = Store(config.STATE_DIR / "koc.db")
    resumed = store.start_run(run_id, {"routing": cfg["models"]["routing"]})
    for stage in args.redo_stage or []:
        n = store.reset_stage(run_id, stage)
        print(f"Làm lại stage '{stage}': xoá {n} checkpoint")
    print(f"run_id={run_id} ({'TIẾP TỤC run cũ' if resumed else 'run mới'})")
    llm = LLM(cfg["models"], store, run_id, crash_after=args.crash_after, use_cache=not args.no_cache)
    t0 = time.perf_counter()
    try:
        result = pipeline.run(cfg, store, run_id, llm)
    except (SimulatedCrash, BudgetExceeded) as e:
        print(f"\nDỪNG: {e}\nTiến độ đã lưu. Chạy lại cùng lệnh (bỏ --crash-after) để tiếp tục.")
        sys.exit(2)
    out = report.write(result, cfg["models"]["routing"], time.perf_counter() - t0)
    print(f"\nChi phí AI: ${result['cost_usd']:.4f} | kết quả: {out['dir']}")
    for i, s in enumerate(result["choice"]["selected"], 1):
        print(f"  {i}. @{s['handle']}  điểm {s['final_score']:.3f}  ~{s['est_cost_vnd'] / 1e6:.1f} tr")


def cmd_status(args):
    cfg = _cfg_with_overrides(args)
    run_id = _run_id(cfg, args.run_id)
    store = Store(config.STATE_DIR / "koc.db")
    rows = store.db.execute(
        "SELECT stage, status, COUNT(*) n FROM stage_items WHERE run_id=? GROUP BY stage, status", (run_id,)
    ).fetchall()
    print(f"run_id={run_id}")
    for r in rows:
        print(f"  {r['stage']:<10} {r['status']:<8} {r['n']}")
    print(f"  chi phí: ${store.run_cost(run_id):.4f}")


def cmd_shortlist(args):
    from koc.sources.kalodata import detail_path, load_creator_list
    from koc.stages.prefilter import funnel_caps, prefilter, shortlist_by_quota
    cfg = config.load_all()
    kept, _ = prefilter(load_creator_list()["creators"], cfg["campaign"])
    caps = funnel_caps(cfg["campaign"])
    for c in shortlist_by_quota(kept, caps["quota"], caps["enrich"],
                                tuple(cfg["campaign"]["prefilter"].get("rank_by_pre_score", ["creators_list"]))):
        mark = "có" if detail_path(c["handle"]).exists() else "THIẾU"
        print(f"{c['handle']:<28} id={c['kalodata_id']}  nguồn={','.join(c['sources'])}  snapshot={mark}")


def cmd_changes(args):
    """Sổ đăng ký creator: ai mới/thay đổi gần đây, ai quá hạn cần lấy lại dữ liệu nguồn."""
    import json as _json
    from koc.registry import Registry
    cfg = config.load_all()
    max_age = cfg["campaign"].get("refresh", {}).get("max_age_days", 14)
    reg = Registry(Store(config.STATE_DIR / "koc.db"), max_age)
    rows = reg.all()
    now = time.time()
    print(f"{len(rows)} creator trong sổ (quá hạn = {max_age} ngày không có thay đổi)")
    for r in rows:
        age = (now - r["last_changed"]) / 86400
        flag = "QUÁ HẠN" if age > max_age else ""
        changes = ", ".join(_json.loads(r["last_changes"] or "[]"))
        print(f"  @{r['handle']:<24} thay đổi gần nhất {age:5.1f} ngày trước: {changes} {flag}")


def cmd_fetch_videos(args):
    """Tải mp4 từ data/kalodata/video_urls.json (link Kalodata có chữ ký, hết hạn nhanh -> chạy ngay)."""
    from koc import media
    res = media.fetch_kalodata_videos()
    print(f"Đã có {res['ok']} video; lỗi {len(res['failed'])}")
    for f in res["failed"]:
        print("  !", f)


def cmd_sanitize(args):
    from koc.sources.kalodata import sanitize_snapshots
    print(f"Đã làm sạch {sanitize_snapshots()} file snapshot (xoá số điện thoại/email trong bio, "
          "thay mã băm liên hệ bằng mã vô nghĩa lh-N)")


def main():
    _setup()
    p = argparse.ArgumentParser(prog="koc")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("run", "status"):
        sp = sub.add_parser(name)
        sp.add_argument("--run-id")
        for stage in ("screen", "video", "rationale"):
            sp.add_argument(f"--{stage}-model")
        if name == "run":
            sp.add_argument("--crash-after", type=int, help="giả lập sự cố sau N lần gọi model thật")
            sp.add_argument("--no-cache", action="store_true", help="không đọc cache LLM (đo chi phí/thời gian chạy nguội)")
            sp.add_argument("--redo-stage", action="append", choices=["enrich", "screen", "video", "rationale"],
                            help="xoá checkpoint của stage để làm lại khi dữ liệu đầu vào đã đổi (cache LLM vẫn dùng)")
    sub.add_parser("shortlist")
    sub.add_parser("fetch-videos")
    sub.add_parser("changes")
    sub.add_parser("sanitize-data")
    ex = sub.add_parser("export-html")
    ex.add_argument("--run-id", default="final")
    sv = sub.add_parser("serve")
    sv.add_argument("--port", type=int, default=8000)
    st = sub.add_parser("scale-test")
    st.add_argument("--sizes", default="5,50,500", help="các số KOC cần tìm, cách nhau dấu phẩy")
    st.add_argument("--seed", type=int, default=7)
    bp = sub.add_parser("bench")
    bp.add_argument("--run-id", help="run có input dùng chung cho mọi model (mặc định: run của cấu hình hiện tại)")
    bp.add_argument("--render-only", action="store_true", help="chỉ dựng lại báo cáo + đề xuất từ số đã đo, không gọi model")
    args = p.parse_args()
    if args.cmd == "export-html":
        from koc.web.server import export_static
        print(f"Đã ghi {export_static(args.run_id)} – bấm đúp để mở, không cần chạy gì")
        return
    if args.cmd == "serve":
        from koc.web.server import serve
        serve(args.port)
        return
    if args.cmd == "scale-test":
        from koc import scale
        scale.main([int(x) for x in args.sizes.split(",")], args.seed)
        return
    if args.cmd == "bench":
        from koc import benchmark
        benchmark.render_only(args.run_id) if args.render_only else benchmark.main(args.run_id)
        return
    {"run": cmd_run, "status": cmd_status, "shortlist": cmd_shortlist, "fetch-videos": cmd_fetch_videos, "changes": cmd_changes,
     "sanitize-data": cmd_sanitize}[args.cmd](args)


if __name__ == "__main__":
    main()
