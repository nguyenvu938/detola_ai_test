"""Điều phối 7 stage của phễu. Mỗi item xong là ghi checkpoint; chạy lại cùng run_id thì resume.

  S0 ingest     đọc danh sách creator từ Kalodata                      0 token
  S1 prefilter  luật: follower, tên brand/shop, có doanh thu ngành       0 token
  S2 enrich     lấy chi tiết Kalodata (nhân khẩu học, video, shop)      0 token
  S3 metrics    điểm định lượng + lọc khán giả nữ                       0 token
  S4 screen     LLM đọc text, 8 creator / lần gọi, song song            rẻ
  S5 video      AI xem video, chỉ top-K, song song                      đắt nhất
  S6 select     tối ưu tổ hợp trong ngân sách                           0 token
  S7 rationale  LLM viết lý do, 1 lần gọi / 10 KOC                       thấp

Số người ở mỗi tầng tỷ lệ với n_koc (funnel_caps), nên cùng code chạy cho 5 hay 500 KOC.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager

from koc.audience import Target
from koc.registry import Registry
from koc.llm.base import LLM, BudgetExceeded, SimulatedCrash
from koc.sources.kalodata import contact_groups, load_creator_detail, load_creator_list
from koc.stages.metrics import compute_metrics
from koc.stages.prefilter import funnel_caps, prefilter, shortlist_by_quota
from koc.stages.rationale import write_rationale
from koc.stages.screen import screen_batch
from koc.stages.select import choose, combine, screen_score
from koc.stages.video import analyze_creator
from koc.store import Store

FATAL = (BudgetExceeded, SimulatedCrash, KeyboardInterrupt)


@contextmanager
def timed(store: Store, run_id: str, stage: str, n_items: int, log):
    t0 = time.perf_counter()
    try:
        yield
    finally:   # ghi cả khi stage bị ngắt giữa chừng, để thời gian cộng dồn qua các lần resume là đúng
        secs = time.perf_counter() - t0
        store.add_timing(run_id, stage, secs, n_items)
        log(f"  [{stage}] {n_items} item, {secs:.1f}s")


def _retryable(store, run_id, stage, item_id, max_attempts) -> bool:
    row = store.get_item(run_id, stage, item_id)
    return row is None or (row["status"] == "failed" and row["attempts"] < max_attempts)


def _run_started(store: Store, run_id: str) -> float:
    """Thời điểm run bắt đầu (lần chạy đầu tiên, kể cả khi đã resume); không có thì lấy hiện tại."""
    row = store.db.execute("SELECT started_at FROM runs WHERE run_id=?", (run_id,)).fetchone()
    return row[0] if row and row[0] else time.time()


def run(cfg: dict, store: Store, run_id: str, llm: LLM, log=print) -> dict:
    camp, models = cfg["campaign"], cfg["models"]
    routing, limits = models["routing"], models["limits"]
    funnel = camp["funnel"]
    caps = funnel_caps(camp)          # số người mỗi tầng phễu, tỷ lệ với n_koc (mở rộng 5 -> 500 KOC)
    funnel_counts = {}

    # S0 + S1: rẻ, chạy lại mỗi lần (tất định)
    with timed(store, run_id, "ingest+prefilter", 0, log):
        creators = load_creator_list()["creators"]
        kept, pre_dropped = prefilter(creators, camp)
        to_enrich = shortlist_by_quota(kept, caps["quota"], caps["enrich"],
                                       tuple(camp["prefilter"].get("rank_by_pre_score", ["creators_list"])))
    funnel_counts.update(ingested=len(creators), after_prefilter=len(kept), enriched_target=len(to_enrich))

    # S2 enrich – checkpoint từng creator
    details = store.stage_outputs(run_id, "enrich")
    with timed(store, run_id, "enrich", len(to_enrich), log):
        for c in to_enrich:
            h = c["handle"]
            if h in details:
                continue
            d = load_creator_detail(h)
            if d is None:
                store.save_item(run_id, "enrich", h, "failed", error="chưa có snapshot chi tiết")
                continue
            store.save_item(run_id, "enrich", h, "done", d)
            details[h] = d
    # So với lần quét trước: ai mới / thay đổi / không đổi / quá hạn (xem koc/registry.py)
    registry = Registry(store, camp.get("refresh", {}).get("max_age_days", 14))
    reg = [registry.observe(c["handle"], details[c["handle"]]) for c in to_enrich if c["handle"] in details]
    funnel_counts["registry"] = {s: sum(r["status"] == s for r in reg) for s in ("new", "changed", "unchanged", "stale")}

    # S3 metrics – tính lại mỗi lần (rẻ, tất định)
    market = cfg["market"]
    rows, metric_dropped = compute_metrics(to_enrich, details, camp, market["rate_card"], market.get("reach_benchmark"))
    # Nhóm kênh dùng chung liên hệ (cùng người quản lý/agency): bước chọn chỉ lấy tối đa 1 kênh mỗi nhóm
    groups = contact_groups(details)
    sizes = {}
    for g in groups.values():
        sizes[g] = sizes.get(g, 0) + 1
    for r in rows:
        g = groups.get(r["handle"])
        r["contact_group"] = g if g and sizes[g] > 1 else None
    funnel_counts["contact_groups"] = sum(1 for s in sizes.values() if s > 1)
    funnel_counts["after_metrics"] = len(rows)

    # S4 screen – phễu thích ứng: sàng lọc từng đợt theo thứ tự điểm, dừng khi đủ ứng viên đạt cổng.
    # Mỗi đợt gửi song song số batch VỪA ĐỦ cho phần còn thiếu (tối đa `concurrency`):
    # 5 KOC thiếu 10 người -> 2 batch; 500 KOC thiếu 1000 người -> `concurrency` batch cùng lúc.
    route = routing["screen"]
    ranked = [r["handle"] for r in rows[: caps["screen"]]]
    screens = store.stage_outputs(run_id, "screen")

    def passes_gate(s: dict) -> bool:
        return s["account_kind"] in funnel["eligible_kinds"] and s["topic_relevance"] >= funnel["min_relevance"]

    def n_eligible() -> int:
        return sum(passes_gate(screens[h]) for h in ranked if h in screens)

    def screen_one(batch: list[str]):
        try:
            out = screen_batch(llm, batch, details, route, camp["campaign"])
            for h in batch:
                store.save_item(run_id, "screen", h, "done", out[h])
                screens[h] = out[h]
        except FATAL:
            raise
        except Exception as e:  # lỗi 1 batch không làm hỏng cả run
            for h in batch:
                store.save_item(run_id, "screen", h, "failed", error=str(e)[:500])
            log(f"  ! screen batch lỗi: {e}")

    queue = [h for h in ranked if h not in screens and _retryable(store, run_id, "screen", h, limits["max_attempts"])]
    bs = route["batch_size"]
    with timed(store, run_id, "screen", len(queue), log), ThreadPoolExecutor(max_workers=limits["concurrency"]) as ex:
        while queue and (missing := caps["video"] - n_eligible()) > 0:
            n_batches = min(limits["concurrency"], -(-missing // bs))       # -(-a // b) = làm tròn lên
            wave, queue = queue[: n_batches * bs], queue[n_batches * bs:]
            for f in [ex.submit(screen_one, wave[i:i + bs]) for i in range(0, len(wave), bs)]:
                f.result()       # lỗi FATAL (hết ngân sách, giả lập sập) được ném lại ở đây
    funnel_counts["screened"] = len([h for h in ranked if h in screens])
    funnel_counts["passed_screen_gate"] = n_eligible()

    # S5 video – chỉ top-K ứng viên đạt cổng, xếp theo điểm tạm (metric + screen)
    route = routing["video"]
    wf = camp["weights"]["final"]
    eligible = [r for r in rows if r["handle"] in screens and passes_gate(screens[r["handle"]])]
    eligible.sort(key=lambda r: wf["metric"] * r["metric_score"] + wf["screen"] * screen_score(screens[r["handle"]]),
                  reverse=True)
    v_targets = [r["handle"] for r in eligible[: caps["video"]]]
    videos = store.stage_outputs(run_id, "video")
    pending = [h for h in v_targets if h not in videos and _retryable(store, run_id, "video", h, limits["max_attempts"])]
    mcfg = models["models"][route["model"]]
    with timed(store, run_id, "video", len(pending), log):
        with ThreadPoolExecutor(max_workers=limits["concurrency"]) as pool:
            futs = {pool.submit(analyze_creator, llm, details[h], camp["campaign"], route, mcfg): h
                    for h in pending}
            fatal = None
            for f in as_completed(futs):
                h = futs[f]
                try:
                    out = f.result()
                    store.save_item(run_id, "video", h, "done", out)
                    videos[h] = out
                except FATAL as e:
                    fatal = fatal or e
                except Exception as e:
                    store.save_item(run_id, "video", h, "failed", error=str(e)[:500])
                    log(f"  ! video {h} lỗi: {e}")
            if fatal:
                raise fatal
    funnel_counts["video_analyzed"] = len([h for h in v_targets if h in videos])

    # S6 select – chỉ người đạt cổng screen và đạt ngưỡng điểm cuối
    gated = {h: s for h, s in screens.items() if passes_gate(s)}
    pool_all = combine(rows, gated, videos, wf, audience_weight=camp["weights"]["metric"]["audience"],
                       photo_post_factor=camp.get("video", {}).get("photo_post_factor", 1.0),
                       target=Target(camp["campaign"]))
    pool_rows = [p for p in pool_all if p["final_score"] >= funnel["min_final_score"]]
    funnel_counts["above_min_score"] = len(pool_rows)
    n_koc = camp["campaign"]["n_koc"]
    # Brief yêu cầu đủ n KOC trong TỔNG ngân sách -> ưu tiên số KOC; phần còn lại dành cho Spark Ads.
    # Dự phòng quảng cáo (research) là mục tiêu mềm: thấp hơn khuyến nghị thì cảnh báo, không bỏ bớt KOC.
    budget = camp["campaign"]["budget_vnd"]
    choice = choose(pool_rows, n_koc, budget)
    recommended_ads = market.get("reserve_for_ads_vnd", 0)
    choice["ads_reserve_vnd"] = choice["reserve_vnd"]
    choice["recommended_ads_vnd"] = recommended_ads
    choice["reserve_vnd"] = 0
    if choice["ads_reserve_vnd"] < recommended_ads:
        choice["ads_note"] = (f"Còn {choice['ads_reserve_vnd'] / 1e6:.2f} tr cho Spark Ads, thấp hơn mức khuyến nghị "
                              f"{recommended_ads / 1e6:.1f} tr: có thể đàm phán phí theo hoa hồng (12–18%) để giữ ngân sách boost.")
    if len(choice["selected"]) < n_koc:
        if len(pool_rows) < n_koc:
            choice["note"] = (f"Chỉ {len(pool_rows)}/{n_koc} KOC đạt ngưỡng điểm {funnel['min_final_score']}. "
                              "Không chọn bù người dưới ngưỡng; cần mở rộng nguồn ứng viên (thêm trang Kalodata, "
                              f"tìm theo video review {camp['campaign']['product']}) rồi chạy lại – các bước đã xong được giữ nguyên.")
        else:
            # Đủ người đạt ngưỡng nhưng không tổ hợp n người nào vừa ngân sách -> chỉ ra phương án gần nhất
            alt = choose(pool_rows, n_koc, 10**15)
            over = alt["total_cost_vnd"] - budget
            choice["alternative"] = {"handles": [s["handle"] for s in alt["selected"]],
                                     "total_cost_vnd": alt["total_cost_vnd"], "over_budget_vnd": over}
            choice["note"] = (f"{len(pool_rows)} KOC đạt ngưỡng nhưng không bộ {n_koc} người nào vừa {budget / 1e6:.0f} tr "
                              f"(bộ {n_koc} tốt nhất tốn {alt['total_cost_vnd'] / 1e6:.2f} tr, vượt {over / 1e6:.2f} tr). "
                              f"Đề xuất {len(choice['selected'])} KOC; muốn đủ {n_koc} thì thêm "
                              + ", ".join(f"@{h}" for h in choice["alternative"]["handles"]
                                          if h not in {s['handle'] for s in choice['selected']})
                              + f" và đàm phán giảm {over / 1e6:.2f} tr (vd bỏ phí cấp mã Spark Ads của 1 KOC, "
                              "hoặc trả theo hoa hồng).")
    choice["below_threshold"] = [{"handle": p["handle"], "final_score": p["final_score"]}
                                 for p in pool_all if p["final_score"] < funnel["min_final_score"]]
    funnel_counts["selected"] = len(choice["selected"])

    # S7 rationale – 1 item cho cả bộ (bộ lớn được chia lô trong write_rationale; lô đã xong nằm trong cache LLM)
    final, done = store.done_output(run_id, "rationale", "final")
    sel_key = [r["handle"] for r in choice["selected"]]
    if choice["selected"] and (not done or final.get("selected") != sel_key):
        with timed(store, run_id, "rationale", len(sel_key), log):
            final = write_rationale(llm, choice["selected"], screens, videos, routing["rationale"], camp["campaign"],
                                    concurrency=limits["concurrency"])
            final["selected"] = sel_key
            store.save_item(run_id, "rationale", "final", "done", final)

    store.finish_run(run_id)
    return {
        "run_id": run_id,
        "campaign": camp["campaign"],
        "registry_changes": [r for r in reg if r["status"] != "unchanged"],
        # Thông tin để người xem biết đây là kết quả ĐÃ LƯU: tạo lúc nào, bằng model nào
        "generated_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(_run_started(store, run_id))),
        "routing": {st: r["model"] for st, r in routing.items()},
        "llm_calls": sum(u["calls"] - (u["cache_hits"] or 0) for u in store.usage_by_stage(run_id)),
        "funnel": funnel_counts,
        "dropped": {"prefilter": pre_dropped, "metrics": metric_dropped},
        "metrics": rows,
        "screens": screens,
        "videos": videos,
        "pool": pool_rows,
        "choice": choice,
        "final": final,
        "usage": store.usage_by_stage(run_id),
        "timings": store.timings(run_id),
        "cost_usd": store.run_cost(run_id),
    }
