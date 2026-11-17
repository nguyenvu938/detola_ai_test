"""`koc scale-test` – đo khả năng mở rộng (5 / 50 / 500 KOC) mà KHÔNG tốn tiền, không cần API key.

Chạy NGUYÊN pipeline thật (đủ 7 stage, checkpoint SQLite, cache, phễu thích ứng, chọn trong ngân sách) trên dữ liệu
giả lập. Chỉ thay 3 chỗ vào/ra bằng bản giả:
  - nguồn Kalodata -> sinh creator giả (25 × số KOC cần tìm),
  - tải video      -> 1 file giả,
  - model AI       -> trả JSON đúng schema, KHÔNG gọi mạng.
Đo thật: số người qua từng tầng phễu, số lần gọi model, thời gian phần code, thời gian giải bài chọn,
dung lượng SQLite, phục hồi sau sự cố ở quy mô lớn.
Dự phóng: token / USD / thời gian chờ model = số lần gọi đo được × số đo THẬT cho mỗi item ở run `final`
(results/final/result.json). Kết quả giả không nói gì về CHẤT LƯỢNG (đã đo ở benchmark), chỉ nói về quy mô.
"""
import copy
import hashlib
import json
import math
import random
import shutil
import threading
import time
from unittest.mock import patch

from koc import config, media, pipeline
from koc.llm.base import LLM, SimulatedCrash
from koc.schemas import ScreenBatch, VideoAnalysis
from koc.stages.prefilter import funnel_caps
from koc.stages.select import choose
from koc.store import Store

SCALE_DIR = config.STATE_DIR / "scale"           # state/ không commit
SOURCES = ["creators_list", "creators_list_video", "creators_list_content", "creators_list_research"]
BUDGET_PER_KOC = 6_000_000                       # 30 tr / 5 KOC của đề, giữ nguyên tỷ lệ khi tăng số KOC
CREATORS_PER_KOC = 25
KALODATA_REQ_PER_S = 1.0                         # Kalodata Open API: tối đa 10 request / 10 giây
KALODATA_POINTS_PER_CALL = 0.1
# Tỷ lệ đạt cổng của model giả = tỷ lệ đo được ở run final (13/16 qua cổng sàng lọc, 8/9 đạt ngưỡng sau video)
P_SCREEN_PASS, P_VIDEO_STRONG = 13 / 16, 8 / 9


# ---------------- dữ liệu Kalodata giả ----------------
def make_data(n_creators: int, seed: int, keywords: list[str]) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    creators, details = [], {}
    n_agencies = max(1, n_creators // 60)
    for i in range(n_creators):
        h = f"sim_{i:05d}"
        followers = int(10 ** rng.uniform(3.7, 6.2))               # 5k–1,6M: một phần bị luật follower loại
        srcs = rng.sample(SOURCES, k=rng.choice([1, 1, 1, 2]))
        brand = rng.random() < 0.06
        creators.append({
            "handle": h, "nickname": f"{h} official store" if brand else h, "kalodata_id": str(7 * 10**18 + i),
            "revenue_vnd": int(10 ** rng.uniform(6, 9.5)) if rng.random() < 0.85 else 0,
            "followers": followers, "content_views": int(followers * rng.uniform(0.5, 30)),
            "engagement_rate": None if rng.random() < 0.3 else round(rng.uniform(0.005, 0.12), 4),
            "sources": srcs, "source_ranks": {s: rng.randint(1, n_creators) for s in srcs}, "revenue_basis": srcs[0],
        })
        videos = []
        for j in range(10):
            on_topic = rng.random() < 0.5
            vid = f"{7 * 10**18 + i * 100 + j}"
            videos.append({"video_id": vid, "url": f"https://www.tiktok.com/@{h}/video/{vid}",
                           "description": f"{vid} " + (f"review {rng.choice(keywords)} " if on_topic else "outfit ngày mới "),
                           "duration_s": rng.randint(15, 90), "views": int(followers * rng.uniform(0.05, 3)),
                           "is_ad": rng.random() < 0.3})
        details[h] = {
            "handle": h, "nickname": h, "followers": followers, "bio": f"review mỹ phẩm {i}",
            "creator_type": "INDEPENDENT" if rng.random() < 0.9 else "MCN",
            "follower_gender": None, "follower_age": None,
            "follower_sex_label": rng.choices(["Majority Female", "Majority Male", None], [0.8, 0.1, 0.1])[0],
            "follower_age_top": rng.choice(["18-24", "25-34", None]),
            "core_metrics": {"revenue_vnd": 10**8, "live_revenue_vnd": 0, "video_revenue_vnd": 10**8},
            "videos": videos, "shops": [{"name": f"shop {rng.randint(1, 300)}"}],
            "products": [{"title": f"kem chống nắng {rng.randint(1, 50)}"}],
            # ~3% kênh dùng chung liên hệ với kênh khác (cùng agency) -> bước chọn tối đa 1 kênh mỗi nhóm
            "contact_keys": [f"agency{rng.randint(0, n_agencies)}"] if rng.random() < 0.03 else [],
        }
    return creators, details


# ---------------- model giả ----------------
def per_item_profile(run_id: str = "final") -> dict:
    """Token / USD / độ trễ cho MỖI item (creator sàng lọc, creator xem video, KOC viết lý do), đo thật ở run `final`."""
    r = json.loads((config.RESULTS_DIR / run_id / "result.json").read_text(encoding="utf-8"))
    items = {"screen": r["funnel"]["screened"], "video": r["funnel"]["video_analyzed"], "rationale": r["funnel"]["selected"]}
    out = {}
    for u in r["usage"]:
        n = items[u["stage"]]
        out[u["stage"]] = {"model": u["model"], "in": u["input_tokens"] / n, "out": u["output_tokens"] / n,
                           "usd": u["cost_usd"] / n, "latency_s": u["avg_latency_ms"] * u["calls"] / n / 1000}
    return out


class FakeModel:
    """Thay adapter thật: trả JSON đúng schema (tất định theo input), token và USD theo số đo thật của run final."""

    def __init__(self, profile: dict):
        self.profile = profile
        self.latency = {}                 # stage -> [độ trễ dự phóng của từng lần gọi]
        self.lock = threading.Lock()

    def complete(self, *, model, system, parts, schema, effort, max_tokens, model_cfg):
        text = parts[0]["text"]
        rng = random.Random(hashlib.sha256(text.encode()).hexdigest())
        if schema is ScreenBatch:
            stage, items = "screen", json.loads(text)
            data = {"creators": [self._screen(p["handle"], rng) for p in items]}
        elif schema is VideoAnalysis:
            stage, items = "video", [None]
            data = self._video(rng)
        else:
            stage, items = "rationale", json.loads(text)
            data = {"summary_vi": "Tóm tắt giả lập.",
                    "kocs": [{"handle": p["handle"], "reason_vi": "giả lập", "evidence_refs": list(p["evidence"])[:3],
                              "risks_vi": "giả lập", "brief_suggestion_vi": "giả lập"} for p in items]}
        p, n = self.profile[stage], len(items)
        with self.lock:
            self.latency.setdefault(stage, []).append(p["latency_s"] * n)
        return data, round(p["in"] * n), round(p["out"] * n), p["usd"] * n

    @staticmethod
    def _screen(handle: str, rng: random.Random) -> dict:
        ok = rng.random() < P_SCREEN_PASS
        return {"handle": handle, "account_kind": "individual_creator" if ok else rng.choice(["shop_seller", "agency_team"]),
                "primary_niche": "skincare_review", "topic_relevance": rng.randint(5, 9) if ok else rng.randint(1, 3),
                "content_signals": [], "competitor_brands": [], "brand_safety_flags": [], "fit_note": "giả lập"}

    @staticmethod
    def _video(rng: random.Random) -> dict:
        strong = rng.random() < P_VIDEO_STRONG
        return {"is_on_topic": strong, "face_on_camera": strong, "product_demo_on_skin": strong,
                "shows_texture_or_finish": strong and rng.random() < 0.7,
                "hook_strength": rng.randint(3, 5) if strong else 1, "production_quality": rng.randint(3, 5) if strong else 1,
                "presenter_gender": "female", "presenter_age_band": "18_24", "risky_claims": [], "style_tags": [],
                "summary_vi": "giả lập", "evidence": [{"at": "00:03", "observation": "giả lập"}], "confidence": 0.8}


# ---------------- chạy 1 kịch bản ----------------
def _fake_download(dummy):
    return lambda post: {"kind": "video", "mp4": dummy, "subtitle": None, "stats": {}}


def run_scenario(n_koc: int, seed: int, profile: dict, crash_after: int | None = None, tag: str = "") -> dict:
    cfg = config.load_all()
    camp = cfg["campaign"]
    camp["campaign"].update(n_koc=n_koc, budget_vnd=BUDGET_PER_KOC * n_koc)
    models = copy.deepcopy(cfg["models"])
    for m in models["models"].values():
        m["provider"] = "fake"
    models["limits"]["max_usd_per_run"] = 10**6      # đo quy mô, không chặn ngân sách
    creators, details = make_data(CREATORS_PER_KOC * n_koc, seed, camp["campaign"]["topic_keywords"])

    work = SCALE_DIR / f"{n_koc}{tag}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    dummy = work / "dummy.mp4"
    dummy.write_bytes(b"\x00" * 1024)
    store = Store(work / "koc.db")
    run_id = f"scale-{n_koc}"
    store.start_run(run_id, {})
    fake = FakeModel(profile)
    crashed = False
    with patch.object(pipeline, "load_creator_list", lambda: {"creators": copy.deepcopy(creators)}), \
         patch.object(pipeline, "load_creator_detail", lambda h: copy.deepcopy(details.get(h))), \
         patch.object(media, "download", _fake_download(dummy)):
        t0 = time.perf_counter()
        if crash_after is not None:      # lần 1 "sập" giữa chừng, lần 2 chạy tiếp cùng run_id
            llm = LLM(models, store, run_id, crash_after=crash_after)
            llm._adapters["fake"] = fake
            try:
                pipeline.run(cfg, store, run_id, llm, log=lambda *_: None)
            except SimulatedCrash:
                crashed = True
        llm = LLM(models, store, run_id)
        llm._adapters["fake"] = fake
        res = pipeline.run(cfg, store, run_id, llm, log=lambda *_: None)
        code_s = time.perf_counter() - t0

    t1 = time.perf_counter()
    choose(res["pool"], n_koc, camp["campaign"]["budget_vnd"])
    select_s = time.perf_counter() - t1
    paid = store.db.execute("SELECT stage, item_ids FROM llm_calls WHERE run_id=? AND cache_hit=0 AND ok=1",
                            (run_id,)).fetchall()
    seen, dup = set(), 0
    for row in paid:                      # item nào bị trả tiền 2 lần ở cùng stage = gọi lặp
        for it in json.loads(row["item_ids"]):
            dup += (row["stage"], it) in seen
            seen.add((row["stage"], it))
    calls = {st: sum(1 for r in paid if r["stage"] == st) for st in ("screen", "video", "rationale")}
    usage = store.usage_by_stage(run_id)
    store.db.close()
    db_mb = (work / "koc.db").stat().st_size / 1e6
    wait = {c: sum(math.ceil(len(v) / c) * (sum(v) / len(v)) for v in fake.latency.values()) for c in (4, 16)}
    caps = funnel_caps(camp)
    f = res["funnel"]
    return {
        "n_koc": n_koc, "budget_vnd": camp["campaign"]["budget_vnd"], "creators_in": f["ingested"],
        "after_prefilter": f["after_prefilter"], "enriched": f["enriched_target"], "after_metrics": f["after_metrics"],
        "caps": caps, "screened": f["screened"], "passed_screen_gate": f["passed_screen_gate"],
        "video_analyzed": f["video_analyzed"], "above_min_score": f["above_min_score"], "selected": f["selected"],
        "booking_vnd": res["choice"]["total_cost_vnd"], "contact_groups": f["contact_groups"],
        "llm_calls": calls, "llm_calls_total": sum(calls.values()),
        "input_tokens": sum(u["input_tokens"] for u in usage), "output_tokens": sum(u["output_tokens"] for u in usage),
        "usd": round(sum(u["cost_usd"] for u in usage), 4),
        "model_wait_s": {str(k): round(v) for k, v in wait.items()},
        "kalodata_calls": f["enriched_target"], "kalodata_points": round(f["enriched_target"] * KALODATA_POINTS_PER_CALL, 1),
        "kalodata_s": round(f["enriched_target"] / KALODATA_REQ_PER_S),
        "code_s": round(code_s, 1), "select_s": round(select_s, 3), "db_mb": round(db_mb, 1),
        "timings": {t["stage"]: round(t["seconds"], 2) for t in res["timings"]},
        "crashed_then_resumed": crashed, "duplicate_paid_items": dup,
        "selected_handles": [s["handle"] for s in res["choice"]["selected"]],
    }


# ---------------- báo cáo ----------------
def _fmt_s(s: float) -> str:
    return f"{s:.0f} giây" if s < 90 else f"{s / 60:.0f} phút" if s < 5400 else f"{s / 3600:.1f} giờ"


def render(out: dict) -> str:
    rows = out["scenarios"]
    head = "| | " + " | ".join(f"**{r['n_koc']} KOC**" for r in rows) + " |"
    L = ["# Đo khả năng mở rộng: 5 → 50 → 500 KOC", "",
         f"> **Dữ liệu đã lưu (cache)**, tạo lúc {out['generated_at']} bằng `uv run koc scale-test` (0 đồng, không cần API key).",
         "> Chạy NGUYÊN pipeline thật trên dữ liệu Kalodata **giả lập** với model **giả** (không gọi mạng). "
         "Số người qua phễu, số lần gọi model, thời gian code, bài chọn, SQLite, phục hồi là **đo thật**. "
         "Token, USD, thời gian chờ model là **dự phóng** = số lần gọi × số đo thật mỗi item ở run `final` "
         f"({', '.join(f'{st}: {p['model']}' for st, p in out['profile'].items())}). "
         "Kết quả giả không đo chất lượng (xem benchmark).", "",
         head, "|---|" + "---|" * len(rows)]

    def row(label, fn):
        L.append(f"| {label} | " + " | ".join(fn(r) for r in rows) + " |")

    row("Ngân sách booking", lambda r: f"{r['budget_vnd'] / 1e6:,.0f} tr")
    row("Creator đầu vào (giả lập)", lambda r: f"{r['creators_in']:,}")
    row("S1 qua luật (0 đồng)", lambda r: f"{r['after_prefilter']:,}")
    row("S2 lấy chi tiết Kalodata (12 × n)", lambda r: f"{r['enriched']:,}")
    row("S3 qua chỉ số khán giả (0 đồng)", lambda r: f"{r['after_metrics']:,}")
    row("S4 LLM sàng lọc: người / lần gọi", lambda r: f"{r['screened']:,} / {r['llm_calls']['screen']}")
    row("S5 AI xem video: người = lần gọi", lambda r: f"{r['video_analyzed']:,}")
    row("S7 viết lý do: lần gọi (10 KOC/lần)", lambda r: f"{r['llm_calls']['rationale']}")
    row("**Chọn được** / chi phí booking", lambda r: f"**{r['selected']}** / {r['booking_vnd'] / 1e6:,.1f} tr")
    row("Tổng lần gọi model", lambda r: f"{r['llm_calls_total']:,} ({r['llm_calls_total'] / r['creators_in']:.0%} số creator đầu vào)")
    row("Token vào / ra (dự phóng)", lambda r: f"{r['input_tokens'] / 1e6:.2f}M / {r['output_tokens'] / 1e6:.2f}M")
    row("**Chi phí AI (dự phóng)**", lambda r: f"**${r['usd']:.2f}** (${r['usd'] / r['n_koc']:.4f}/KOC)")
    row("Chờ model, song song 4 / 16 (dự phóng)",
        lambda r: f"{_fmt_s(r['model_wait_s']['4'])} / {_fmt_s(r['model_wait_s']['16'])}")
    row("Kalodata API: lần gọi / điểm / thời gian ở 1 req/s", lambda r: f"{r['kalodata_calls']:,} / {r['kalodata_points']:,} / {_fmt_s(r['kalodata_s'])}")
    row("Thời gian phần code (đo thật)", lambda r: f"{r['code_s']} giây" if r["code_s"] >= 0.1 else "< 0.1 giây")
    row("Giải bài chọn trong ngân sách (đo thật)",
        lambda r: f"{r['select_s'] * 1000:.0f} ms" if r["select_s"] >= 0.001 else "< 1 ms")
    row("SQLite (checkpoint + cache)", lambda r: f"{r['db_mb']} MB")
    rs = out.get("resume")
    if rs:
        L += ["", f"**Phục hồi ở quy mô {rs['n_koc']} KOC:** cho \"sập\" sau {rs['crash_after']} lần gọi model rồi chạy lại cùng "
              f"run: {rs['llm_calls_total']} lần gọi trả tiền (chạy liền một lèo: {rs['clean_calls']}), "
              f"**{rs['duplicate_paid_items']} item bị gọi lặp**, chọn ra {rs['selected']} KOC "
              f"({'trùng' if rs['same_selection'] else 'khác'} bộ chọn của lần chạy liền)."]
    L += ["", "Cách đọc:",
          "- Mọi tầng phễu tỷ lệ với số KOC (`*_per_koc` trong `config/campaign.toml`), nên chi phí AI tăng **tuyến tính** "
          "theo số KOC, không theo số creator đầu vào: phần lớn creator bị loại ở các bước 0 đồng.",
          "- Nút thắt thời gian ở 500 KOC là **lấy chi tiết Kalodata** (giới hạn 10 request/10 giây) và **chờ model** "
          "(tăng `concurrency` trong `config/models.toml` theo hạn mức RPM của tài khoản). Code chỉ chiếm vài chục giây.",
          "- Run 500 KOC cần nâng `max_usd_per_run` (mặc định $1, chặn hóa đơn bất ngờ) lên trên mức dự phóng.",
          "- Bài chọn: n ≤ 6 vét cạn (chính xác); n lớn dùng nhân tử Lagrange + đổi chỗ (test so với vét cạn ở cỡ nhỏ)."]
    return "\n".join(L) + "\n"


def main(sizes: list[int], seed: int = 7):
    profile = per_item_profile()
    out = {"generated_at": time.strftime("%Y-%m-%d %H:%M"), "seed": seed, "profile": profile, "scenarios": []}
    for n in sizes:
        print(f"Kịch bản {n} KOC ...", flush=True)
        r = run_scenario(n, seed, profile)
        print(f"  chọn {r['selected']}/{n}, {r['llm_calls_total']} lần gọi model, ~${r['usd']:.2f}, code {r['code_s']}s")
        out["scenarios"].append(r)
    mid = next((r for r in out["scenarios"] if r["n_koc"] == 50), None)
    if mid:      # phục hồi ở quy mô 50 KOC: sập ở khoảng giữa rồi chạy tiếp
        crash_after = mid["llm_calls_total"] // 2
        print(f"Phục hồi 50 KOC: sập sau {crash_after} lần gọi ...", flush=True)
        r = run_scenario(50, seed, profile, crash_after=crash_after, tag="-resume")
        out["resume"] = {"n_koc": 50, "crash_after": crash_after, "llm_calls_total": r["llm_calls_total"],
                         "clean_calls": mid["llm_calls_total"], "duplicate_paid_items": r["duplicate_paid_items"],
                         "selected": r["selected"], "same_selection": r["selected_handles"] == mid["selected_handles"],
                         "crashed": r["crashed_then_resumed"]}
    (config.RESULTS_DIR / "scale_test.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    (config.RESULTS_DIR / "scale_test.md").write_text(render(out), encoding="utf-8")
    print("Đã ghi results/scale_test.md và results/scale_test.json")
    return out
