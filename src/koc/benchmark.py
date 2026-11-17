"""koc bench – chạy lại 3 bước LLM trên CÙNG input với nhiều model (Claude, Gemini, DeepSeek),
so chi phí / thời gian / chất lượng.

Cần chạy `koc run` trước: benchmark lấy đúng danh sách creator, bài đăng và bộ KOC của run đó
để mọi model nhận input giống hệt nhau.
Chất lượng đo bằng độ khớp với NHÃN THAM CHIẾU = đồng thuận của model mạnh nhất mỗi hãng (effort cao):
trường phân loại lấy đa số, trường điểm lấy trung vị. Nếu có eval/golden_labels.csv (nhãn do người gán)
thì đo thêm độ khớp với người – đây mới là thước đo cuối cùng.
"""
import csv
import json
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from statistics import mean, median

from koc import config, media
from koc.audience import Target
from koc.cli import _run_id
from koc.llm.base import LLM
from koc.stages.rationale import write_rationale
from koc.stages.screen import screen_batch
from koc.stages.select import choose, combine
from koc.stages.video import analyze_video
from koc.store import Store

FIELDS = {
    "screen": (["account_kind", "primary_niche"], ["topic_relevance"]),
    "video": (["is_on_topic", "face_on_camera", "product_demo_on_skin", "shows_texture_or_finish", "presenter_gender"],
              ["hook_strength", "production_quality"]),
}
KEY_ENV = config.KEY_ENV


# ---------------- chạy 1 biến thể (1 bước × 1 model × 1 effort) ----------------
def input_signature(result: dict) -> str:
    """Băm danh sách item đầu vào: input khác -> lần đo khác (không trộn số liệu giữa các lần)."""
    items = [sorted(result["screens"]), sorted((h, v["video_id"]) for h, v in result["videos"].items()),
             [s["handle"] for s in result["choice"]["selected"]]]
    return config.config_hash(items)[:6]


def run_variant(stage, model, effort, cfg, store, details, result):
    camp = cfg["campaign"]["campaign"]
    run = f"bench-{result['run_id']}-{input_signature(result)}-{stage}-{model}-{effort}"
    store.start_run(run, {"stage": stage, "model": model, "effort": effort})
    models_cfg = {**cfg["models"], "limits": {**cfg["models"]["limits"],
                                              "max_usd_per_run": cfg["models"]["benchmark"]["max_usd_per_variant"]}}
    llm = LLM(models_cfg, store, run, cache_namespace=run)
    route = {**cfg["models"]["routing"][stage], "model": model, "effort": effort}
    outputs, errors = {}, []
    t0 = time.perf_counter()
    if stage == "screen":
        handles = list(result["screens"])
        for i in range(0, len(handles), route["batch_size"]):
            batch = handles[i: i + route["batch_size"]]
            try:
                outputs.update(screen_batch(llm, batch, details, route, camp))
            except Exception as e:
                errors.append(str(e)[:200])
    elif stage == "video":
        mcfg = cfg["models"]["models"][model]

        def one(h):
            v = result["videos"][h]
            post = next(x for x in details[h]["videos"] if x["video_id"] == v["video_id"])
            return h, analyze_video(llm, h, post, media.download(post), route, mcfg, camp)["analysis"]

        with ThreadPoolExecutor(max_workers=4) as pool:
            for fut in [pool.submit(one, h) for h in result["videos"]]:
                try:
                    h, a = fut.result()
                    outputs[h] = a
                except Exception as e:
                    errors.append(str(e)[:200])
    else:  # rationale
        try:
            outputs["final"] = write_rationale(llm, result["choice"]["selected"], result["screens"],
                                               result["videos"], route, camp)
        except Exception as e:
            errors.append(str(e)[:200])
    stats, source = real_call_stats(store, run, stage, model)
    if stats is None and effort == route_effort(cfg, stage):
        # Toàn cache hit vì input trùng run pipeline -> lấy số của chính các lần gọi thật trong run đó
        stats, source = real_call_stats(store, result["run_id"], stage, model)
        source = f"lần gọi thật trong run {result['run_id']} (cùng model, cùng input)" if stats else None
    stats = stats or {"seconds": round(time.perf_counter() - t0, 1), "input_tokens": 0, "output_tokens": 0,
                      "cost_usd": 0.0, "avg_latency_ms": None, "calls": 0}
    return {
        "stage": stage, "model": model, "provider": cfg["models"]["models"][model]["provider"], "effort": effort,
        "outputs": outputs, "errors": errors, "stats_source": source, **stats,
    }


def route_effort(cfg: dict, stage: str) -> str | None:
    return cfg["models"]["routing"][stage].get("effort")


def real_call_stats(store, run: str, stage: str, model: str) -> tuple[dict | None, str | None]:
    """Chi phí / token / thời gian từ các lần gọi THẬT (không tính cache hit) trong sổ llm_calls.
    Thời gian chạy = từ lúc lần gọi đầu bắt đầu tới lúc lần gọi cuối xong (đúng cả khi gọi song song)."""
    rows = store.db.execute(
        """SELECT input_tokens, output_tokens, cost_usd, latency_ms, created_at FROM llm_calls
           WHERE run_id=? AND stage=? AND model=? AND cache_hit=0 AND ok=1""", (run, stage, model)
    ).fetchall()
    if not rows:
        return None, None
    start = min(r["created_at"] - (r["latency_ms"] or 0) / 1000 for r in rows)
    return {
        "calls": len(rows),
        "seconds": round(max(r["created_at"] for r in rows) - start, 1),
        "input_tokens": sum(r["input_tokens"] for r in rows),
        "output_tokens": sum(r["output_tokens"] for r in rows),
        "cost_usd": sum(r["cost_usd"] for r in rows),
        "avg_latency_ms": mean(r["latency_ms"] for r in rows),
    }, "lần gọi thật của biến thể này"


# ---------------- nhãn tham chiếu và độ khớp ----------------
def consensus(ref_outputs: list[dict], exact: list[str], num: list[str]) -> dict:
    """Nhãn tham chiếu cho từng item, chỉ khi có ít nhất 2 model tham chiếu trả lời:
    - trường phân loại: giá trị được ĐA SỐ THẬT (> 1/2) đồng ý; hoà thì bỏ trường đó (không cho model nào thắng mặc định)
    - trường điểm: trung vị."""
    out = {}
    for k in set().union(*(set(o) for o in ref_outputs)) if ref_outputs else set():
        vals = [o[k] for o in ref_outputs if k in o]
        if len(vals) < 2:
            continue
        item = {}
        for f in exact:
            value, n = Counter(v[f] for v in vals).most_common(1)[0]
            if n * 2 > len(vals):
                item[f] = value
        item.update({f: median(v[f] for v in vals) for f in num})
        out[k] = item
    return out


def agreement(outputs: dict, ref: dict, exact: list[str], num: list[str]) -> dict:
    keys = [k for k in outputs if k in ref]
    if not keys:
        return {"n": 0, "exact_avg": None}
    res = {"n": len(keys)}
    for f in exact:
        ks = [k for k in keys if f in ref[k]]           # bỏ item mà tham chiếu hoà ở trường này
        res[f] = mean(outputs[k][f] == ref[k][f] for k in ks) if ks else None
    for f in num:
        res[f + "_mae"] = mean(abs(outputs[k][f] - ref[k][f]) for k in keys)
    vals = [res[f] for f in exact if res[f] is not None]
    res["exact_avg"] = mean(vals) if vals else None
    return res


# ---------------- nhãn người (tuỳ chọn) ----------------
GOLDEN_COLUMNS = ["handle", "video_url", "account_kind", "face_on_camera", "product_demo_on_skin", "note"]


def write_golden_template(result: dict):
    """Tạo file mẫu để NGƯỜI gán nhãn (cột nhãn để trống). Không bao giờ để AI điền nhãn vàng."""
    p = config.ROOT / "eval" / "golden_labels_TEMPLATE.csv"
    p.parent.mkdir(exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(GOLDEN_COLUMNS)
        for h in result["screens"]:
            v = result["videos"].get(h)
            w.writerow([h, v["url"] if v else "", "", "", "", ""])
    print(f"Đã tạo {p}: xem kênh/video, điền nhãn, lưu thành eval/golden_labels.csv rồi chạy lại `koc bench`.")


def load_golden() -> dict:
    p = config.ROOT / "eval" / "golden_labels.csv"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return {r["handle"]: r for r in csv.DictReader(f) if r.get("account_kind") or r.get("face_on_camera")}


def human_agreement(outputs: dict, golden: dict, field: str) -> float | None:
    ks = [h for h in outputs if (golden.get(h) or {}).get(field)]
    if not ks:
        return None
    return mean(str(outputs[h][field]).lower() == golden[h][field].strip().lower() for h in ks)


# ---------------- chương trình chính ----------------
def main(run_id: str | None = None):
    cfg = config.load_all()
    run_id = _run_id(cfg, run_id)
    result = json.loads((config.RESULTS_DIR / run_id / "result.json").read_text(encoding="utf-8"))
    store = Store(config.STATE_DIR / "koc.db")
    details = store.stage_outputs(run_id, "enrich")
    b, mcat = cfg["models"]["benchmark"], cfg["models"]["models"]

    skipped = {}

    def available(m):
        env = KEY_ENV[mcat[m]["provider"]]
        if not os.environ.get(env):
            skipped[m] = f"thiếu {env}"
            return False
        return True

    report = {"run_id": run_id, "stages": {}, "skipped": skipped}
    for stage in ("screen", "video", "rationale"):
        eff = b["effort"] if stage != "rationale" else cfg["models"]["routing"]["rationale"].get("effort", "medium")
        variants = [(m, eff) for m in b["models"]]
        if stage != "rationale":
            variants += [(m, b["reference_effort"]) for m in b["reference_models"]]
        if stage == "video":
            variants = [(m, e) for m, e in variants if mcat[m].get("vision") or mcat[m].get("video")]
        runs = []
        for model, effort in variants:
            if not available(model):
                continue
            print(f"[bench] {stage:<9} {model:<22} effort={effort}")
            runs.append(run_variant(stage, model, effort, cfg, store, details, result))
        report["stages"][stage] = runs

    # Nhãn tham chiếu đồng thuận + độ khớp
    for stage, (exact, num) in FIELDS.items():
        runs = report["stages"][stage]
        refs = [r for r in runs if r["model"] in b["reference_models"] and r["effort"] == b["reference_effort"]]
        ref = consensus([r["outputs"] for r in refs], exact, num)
        report.setdefault("reference", {})[stage] = {"models": [r["model"] for r in refs], "items": len(ref)}
        for r in runs:
            r["agreement_vs_ref"] = agreement(r["outputs"], ref, exact, num)

    # Ảnh hưởng tới quyết định cuối: nếu dùng model X cho cả screen + video thì bộ KOC có đổi không?
    camp = cfg["campaign"]
    wf, aw = camp["weights"]["final"], camp["weights"]["metric"]["audience"]
    funnel = camp["funnel"]
    budget = camp["campaign"]["budget_vnd"]   # giống pipeline: ưu tiên đủ số KOC trong tổng ngân sách
    picks = {}
    for r_s in report["stages"]["screen"]:
        r_v = next((r for r in report["stages"]["video"]
                    if (r["model"], r["effort"]) == (r_s["model"], r_s["effort"])), None)
        if not r_v:
            continue
        gated = {h: s for h, s in r_s["outputs"].items()
                 if s["account_kind"] in funnel["eligible_kinds"] and s["topic_relevance"] >= funnel["min_relevance"]}
        vids = {h: {**result["videos"][h], "analysis": a} for h, a in r_v["outputs"].items()}
        pool = [p for p in combine(result["metrics"], gated, vids, wf, audience_weight=aw,
                                   photo_post_factor=camp.get("video", {}).get("photo_post_factor", 1.0),
                                   target=Target(camp["campaign"]))
                if p["final_score"] >= funnel["min_final_score"]]
        picks[(r_s["model"], r_s["effort"])] = {s["handle"] for s in choose(pool, camp["campaign"]["n_koc"], budget)["selected"]}
    pipeline_pick = {s["handle"] for s in result["choice"]["selected"]}
    report["picks"] = [{"model": m, "effort": e, "selected": sorted(sel),
                        "jaccard_vs_pipeline": (len(sel & pipeline_pick) / len(sel | pipeline_pick)) if sel | pipeline_pick else None}
                       for (m, e), sel in picks.items()]

    for r in report["stages"]["rationale"]:
        fin = r["outputs"].get("final")
        r["citation_check"] = fin["citation_check"] if fin else None
        r["avg_reason_chars"] = mean(len(k["reason_vi"]) for k in fin["rationale"]["kocs"]) if fin else None

    golden = load_golden()
    if golden:
        for r in report["stages"]["screen"]:
            r["agreement_vs_human"] = human_agreement(r["outputs"], golden, "account_kind")
        for r in report["stages"]["video"]:
            r["agreement_vs_human"] = human_agreement(r["outputs"], golden, "face_on_camera")
    else:
        write_golden_template(result)

    report["recommendation"] = recommend(report, result, b, cfg["models"]["routing"], cfg["models"]["models"])
    report["generated_at"] = time.strftime("%Y-%m-%d %H:%M")
    report["total_cost_usd"] = sum(r["cost_usd"] for runs in report["stages"].values() for r in runs)

    raw = {s: {f"{r['model']}|{r['effort']}": r["outputs"] for r in runs} for s, runs in report["stages"].items()}
    (config.RESULTS_DIR / "benchmark_outputs.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for runs in report["stages"].values():
        for r in runs:
            r.pop("outputs", None)
    (config.RESULTS_DIR / "benchmark_models.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (config.RESULTS_DIR / "benchmark_models.md").write_text(render(report, result, b), encoding="utf-8")
    print(f"Đã ghi {config.RESULTS_DIR / 'benchmark_models.md'}")


def _pct(x):
    return "–" if x is None else f"{x:.0%}"


# ---------------- đề xuất model cho từng bước ----------------
def _units(result: dict) -> tuple[dict, dict]:
    """Số item mỗi bước đã xử lý trong benchmark, và số item cần cho MỖI KOC được chọn (theo phễu thực tế)."""
    n_sel = max(1, len(result["choice"]["selected"]))
    f = result["funnel"]
    items = {"screen": max(1, len(result["screens"])), "video": max(1, len(result["videos"])), "rationale": 1}
    per_koc = {"screen": f["screened"] / n_sel, "video": f["video_analyzed"] / n_sel, "rationale": 1 / n_sel}
    return items, per_koc


def recommend(rep: dict, result: dict, b: dict, routing: dict, models: dict | None = None) -> dict:
    """Luật chọn: model RẺ NHẤT đạt độ khớp tham chiếu >= min_agreement và không lỗi.
    Không model nào đạt thì chọn model khớp cao nhất. Viết lý do: rẻ nhất có 100% trích dẫn hợp lệ."""
    min_agree = b.get("min_agreement", 0.9)
    items, per_koc = _units(result)
    is_ref = lambda r: r["model"] in b["reference_models"] and r["effort"] == b["reference_effort"]  # noqa: E731
    cost500 = lambda r, st: r["cost_usd"] / items[st] * per_koc[st] * 500  # noqa: E731
    out = {"min_agreement": min_agree, "stages": {}}

    for st in ("screen", "video"):
        # cost_usd = 0 nghĩa là chưa đo được chi phí (vd toàn cache hit) -> không được coi là "rẻ nhất"
        valid = [r for r in rep["stages"].get(st, []) if not is_ref(r) and not r["errors"] and r["cost_usd"] > 0
                 and (r.get("agreement_vs_ref") or {}).get("exact_avg") is not None]
        if not valid:
            continue
        agree = lambda r: r["agreement_vs_ref"]["exact_avg"]  # noqa: E731
        best = max(valid, key=lambda r: (agree(r), -r["cost_usd"]))
        passing = [r for r in valid if agree(r) >= min_agree]
        cheapest_ok = min(passing, key=lambda r: r["cost_usd"]) if passing else best
        chosen = cheapest_ok
        # Nâng cấp đáng giá: khớp cao hơn >= min_gain mà chỉ tốn thêm <= max_extra USD cho 500 KOC
        min_gain, max_extra = b.get("upgrade_min_gain", 0.05), b.get("upgrade_max_extra_usd_500", 2.0)
        upgrades = [r for r in passing if agree(r) - agree(cheapest_ok) >= min_gain
                    and cost500(r, st) - cost500(cheapest_ok, st) <= max_extra]
        if upgrades:
            chosen = max(upgrades, key=lambda r: (agree(r), -r["cost_usd"]))
            why = (f"khớp {agree(chosen):.0%}, cao hơn model rẻ nhất đạt ngưỡng ({cheapest_ok['model']}, "
                   f"{agree(cheapest_ok):.0%}) {(agree(chosen) - agree(cheapest_ok)) * 100:.0f} điểm % mà chỉ tốn thêm "
                   f"${cost500(chosen, st) - cost500(cheapest_ok, st):.2f} cho 500 KOC (ngưỡng nâng cấp: ≥ "
                   f"{min_gain * 100:.0f} điểm %, ≤ ${max_extra:.0f}).")
        elif passing:
            ratio = best["cost_usd"] / chosen["cost_usd"] if chosen["cost_usd"] else None
            why = (f"rẻ nhất trong các model khớp tham chiếu ≥ {min_agree:.0%}: khớp {agree(chosen):.0%}, "
                   f"{chosen['cost_usd'] / items[st]:.5f} USD/item. Model khớp cao nhất là {best['model']} "
                   f"({agree(best):.0%})" + (f", đắt hơn {ratio:.0f} lần" if ratio and ratio >= 1.5 else "")
                   + (f" nhưng chỉ hơn {(agree(best) - agree(chosen)) * 100:.0f} điểm %" if best is not chosen else "")
                   + (f"; không model nào vừa hơn ≥ {min_gain * 100:.0f} điểm % vừa tốn thêm ≤ ${max_extra:.0f}/500 KOC"
                      if best is not chosen else ""))
        else:
            why = f"không model nào đạt {min_agree:.0%}; chọn model khớp cao nhất ({agree(best):.0%})"
        out["stages"][st] = {
            "cheapest_passing": cheapest_ok["model"],
            "model": chosen["model"], "effort": chosen["effort"], "agreement": agree(chosen),
            "usd_per_item": chosen["cost_usd"] / items[st], "usd_500_koc": cost500(chosen, st),
            "avg_latency_s": (chosen.get("avg_latency_ms") or 0) / 1000,
            "best_quality": {"model": best["model"], "agreement": agree(best), "usd_500_koc": cost500(best, st)},
            "current": routing[st]["model"], "why": why,
        }

    rat = [r for r in rep["stages"].get("rationale", []) if not r["errors"] and r["cost_usd"] > 0
           and (r.get("citation_check") or {}).get("valid_rate") == 1.0]
    if rat:
        chosen = min(rat, key=lambda r: r["cost_usd"])
        out["stages"]["rationale"] = {
            "model": chosen["model"], "effort": chosen["effort"], "agreement": None,
            "usd_per_item": chosen["cost_usd"], "usd_500_koc": cost500(chosen, "rationale"),
            "avg_latency_s": (chosen.get("avg_latency_ms") or 0) / 1000, "current": routing["rationale"]["model"],
            "why": (f"rẻ nhất trong {len(rat)} model có 100% mã bằng chứng hợp lệ (kiểm bằng code). "
                    "Văn phong không đo tự động được: nên đọc 1 bản mẫu trước khi đổi (results/benchmark_outputs.json)."),
        }

    # Chi phí dự phóng 500 KOC theo phương án định tuyến
    def plan_cost(pick: dict) -> float | None:
        total = 0.0
        for st, model in pick.items():
            r = next((x for x in rep["stages"].get(st, []) if x["model"] == model and not is_ref(x) and not x["errors"]), None)
            if r is None:
                return None
            total += cost500(r, st)
        return total

    # Độ ổn định: mỗi KOC được bao nhiêu % biến thể (cùng model cho sàng lọc + video) chọn
    picks = rep.get("picks") or []
    if picks:
        counts = Counter(h for p in picks for h in p["selected"])
        out["stability"] = [{"handle": h, "share": n / len(picks), "in_pipeline": h in
                             {s["handle"] for s in result["choice"]["selected"]}} for h, n in counts.most_common()]

    rec_pick = {st: v["model"] for st, v in out["stages"].items()}
    before = {st: (result.get("routing") or {}).get(st, routing[st]["model"]) for st in rec_pick}
    options = [("Đề xuất (theo benchmark)", rec_pick),
               (f"Lúc chạy run {result.get('run_id', '?')}", before),
               ("Toàn Claude Opus 5.5", {st: "claude-opus-5-5" for st in rec_pick})]
    out["providers"] = by_provider(rep, b, valid_fn=lambda r: not is_ref(r) and not r["errors"] and r["cost_usd"] > 0,
                                   cost500=cost500, min_agree=min_agree, models=models or {})
    for p in out["providers"]:
        options.append((f"Chỉ dùng {p['name']}", p["plan"]))
        if p["cheapest_plan"] != p["plan"]:
            options.append((f"Chỉ dùng {p['name']}, model rẻ nhất mỗi bước (có bước chưa đạt ngưỡng)", p["cheapest_plan"]))
    out["run_id"] = result.get("run_id")
    for p in out["providers"]:            # lý do không chọn hãng này ở từng bước (web và báo cáo dùng chung)
        for st, c in p["stages"].items():
            if c:
                c["why"] = why_not(out, st, p)
    out["plans"] = [{"name": n, "routing": r, "usd_500_koc": plan_cost(r)} for n, r in options]
    # Tỷ lệ chi phí theo hãng trong phương án đề xuất (500 KOC)
    share = {}
    for st, v in out["stages"].items():
        name = PROVIDERS.get(v["model"].split("-")[0], v["model"])
        share[name] = share.get(name, 0) + v["usd_500_koc"]
    total = sum(share.values()) or 1
    out["provider_share"] = [{"name": k, "usd_500_koc": u, "share": u / total} for k, u in share.items()]
    return out


PROVIDERS = {"claude": "Anthropic (Claude)", "gemini": "Google (Gemini)", "deepseek": "DeepSeek"}


def _input_mode(mcfg: dict) -> str:
    if mcfg.get("video"):
        return "video gốc" + (" có tiếng" if mcfg.get("audio") else "")
    return "6 khung hình + phụ đề" if mcfg.get("vision") else "không đọc được ảnh"


def by_provider(rep: dict, b: dict, valid_fn, cost500, min_agree: float, models: dict) -> list[dict]:
    """So sánh theo HÃNG: với mỗi hãng và mỗi bước, model rẻ nhất đạt ngưỡng và model khớp cao nhất của hãng đó.
    Từ đó dựng phương án "chỉ dùng 1 hãng" để thấy phải trả bao nhiêu / mất bao nhiêu độ chính xác khi khoá 1 nhà cung cấp."""
    out = []
    for prefix, name in PROVIDERS.items():
        entry = {"name": name, "stages": {}, "plan": {}, "cheapest_plan": {}}
        for st in ("screen", "video", "rationale"):
            runs = [r for r in rep["stages"].get(st, []) if r["model"].startswith(prefix + "-") and valid_fn(r)]
            if st == "rationale":
                runs = [r for r in runs if (r.get("citation_check") or {}).get("valid_rate") == 1.0]
                score = lambda r: (r.get("citation_check") or {}).get("valid_rate")  # noqa: E731
            else:
                runs = [r for r in runs if (r.get("agreement_vs_ref") or {}).get("exact_avg") is not None]
                score = lambda r: r["agreement_vs_ref"]["exact_avg"]  # noqa: E731
            if not runs:
                entry["stages"][st] = None
                continue
            best = max(runs, key=lambda r: (score(r), -r["cost_usd"]))
            passing = [r for r in runs if score(r) >= (1.0 if st == "rationale" else min_agree)]
            pick = min(passing, key=lambda r: r["cost_usd"]) if passing else best
            cheapest = min(runs, key=lambda r: r["cost_usd"])

            def card(r):
                a = r.get("agreement_vs_ref") or {}
                return {"model": r["model"], "agreement": score(r), "usd_500_koc": cost500(r, st),
                        "latency_s": (r.get("avg_latency_ms") or 0) / 1000,
                        "input": _input_mode(models.get(r["model"], {})) if st == "video" else None,
                        "n": a.get("n"), "fields": {f: a.get(f) for f in FIELDS.get(st, ([], []))[0]}}
            entry["stages"][st] = {"pick": card(pick), "passes": bool(passing), "best": card(best),
                                   "cheapest": card(cheapest), "tested": sorted({r["model"] for r in runs})}
            entry["plan"][st] = pick["model"]
            entry["cheapest_plan"][st] = cheapest["model"]
        if prefix == "deepseek":
            no_vision = [m for m, c in models.items() if m.startswith("deepseek-") and not c.get("vision")]
            entry["note"] = (f"{', '.join(no_vision)} không đọc được ảnh nên không tham gia bước xem video"
                             if no_vision else "")
        out.append(entry)
    return out


STAGE_VI = {"screen": "Sàng lọc", "video": "Xem video", "rationale": "Viết lý do"}
FIELD_VI = {"account_kind": "Loại tài khoản", "primary_niche": "Ngách", "is_on_topic": "Đúng chủ đề",
            "face_on_camera": "Lộ mặt", "product_demo_on_skin": "Thử sản phẩm trên da",
            "shows_texture_or_finish": "Kết cấu / độ hoàn thiện", "presenter_gender": "Giới tính người dẫn"}


def why_not(rec: dict, st: str, p: dict) -> str:
    """1 câu: vì sao không dùng hãng p cho bước st (so với model đề xuất)."""
    c, chosen = p["stages"].get(st), rec["stages"].get(st)
    if not chosen:
        return ""
    if c is None:
        return p.get("note") or "không có model phù hợp"
    if c["pick"]["model"] == chosen["model"]:
        return "được chọn"
    pk, parts = c["pick"], []
    if st != "rationale" and not c["passes"]:
        parts.append(f"chưa model nào đạt {rec['min_agreement']:.0%}")
    if st != "rationale" and chosen["agreement"] is not None and pk["agreement"] < chosen["agreement"] - 1e-9:
        parts.append(f"khớp thấp hơn {(chosen['agreement'] - pk['agreement']) * 100:.0f} điểm %")
    ratio = pk["usd_500_koc"] / chosen["usd_500_koc"] if chosen["usd_500_koc"] else None
    if ratio and ratio >= 1.2:
        parts.append(f"đắt hơn {ratio:.1f} lần")
    elif ratio and ratio <= 0.83:
        parts.append(f"rẻ hơn {1 / ratio:.1f} lần")
    elif ratio:
        parts.append("chi phí ngang nhau")
    if chosen["avg_latency_s"] and pk["latency_s"] and pk["latency_s"] < chosen["avg_latency_s"] / 1.5:
        parts.append(f"nhanh hơn {chosen['avg_latency_s'] / pk['latency_s']:.1f} lần")
    elif chosen["avg_latency_s"] and pk["latency_s"] > chosen["avg_latency_s"] * 1.5:
        parts.append(f"chậm hơn {pk['latency_s'] / chosen['avg_latency_s']:.1f} lần")
    return "; ".join(parts) or "ngang nhau"


def render_providers(rec: dict) -> list[str]:
    provs = rec.get("providers") or []
    if not provs:
        return []
    L = ["## So sánh theo hãng: Anthropic, Google, DeepSeek", "",
         "Mỗi ô: model **rẻ nhất đạt ngưỡng** của hãng đó (không có thì model khớp cao nhất), độ khớp tham chiếu, chi phí "
         "cho 500 KOC, độ trễ mỗi lần gọi; dòng dưới: vì sao không dùng hãng đó so với model đề xuất.", "",
         "| Bước | " + " | ".join(p["name"] for p in provs) + " |", "|---|" + "---|" * len(provs)]
    for st in ("screen", "video", "rationale"):
        cells = []
        for p in provs:
            c = p["stages"].get(st)
            if c is None:
                cells.append("–")
                continue
            pk = c["pick"]
            agree = (f"trích dẫn {pk['agreement']:.0%}" if st == "rationale" else f"khớp {pk['agreement']:.0%}"
                     + ("" if c["passes"] else " (chưa đạt)"))
            extra = f"<br>{pk['input']}" if pk.get("input") else ""
            best = c["best"]
            if st != "rationale" and best["model"] != pk["model"]:
                extra += f"<br>khớp cao nhất: {best['model']} {best['agreement']:.0%}, ${best['usd_500_koc']:.2f}"
            ch = c["cheapest"]
            if st != "rationale" and ch["model"] not in (pk["model"], best["model"]):
                extra += (f"<br>rẻ nhất: {ch['model']} {ch['agreement']:.0%}, ${ch['usd_500_koc']:.2f}, "
                          f"{ch['latency_s']:.1f}s")
            why = c.get("why") or why_not(rec, st, p)
            why = f"**{why}**" if why == "được chọn" else f"*{why}*"
            cells.append(f"{pk['model']}<br>{agree} · ${pk['usd_500_koc']:.2f} · {pk['latency_s']:.1f}s{extra}<br>{why}")
        L.append(f"| {STAGE_VI[st]} | " + " | ".join(cells) + " |")
    plans = {pl["name"]: pl["usd_500_koc"] for pl in rec.get("plans", [])}
    L.append("| **Chỉ dùng hãng này, 500 KOC** | " + " | ".join(
        "–" if plans.get(f"Chỉ dùng {p['name']}") is None else f"**${plans[f'Chỉ dùng {p['name']}']:.2f}**"
        for p in provs) + " |")
    L.append("")
    for st in ("screen", "video"):
        rows = [(p["name"], p["stages"].get(st)) for p in provs if p["stages"].get(st)]
        if not rows:
            continue
        fields = list(rows[0][1]["pick"]["fields"])
        n = rows[0][1]["pick"]["n"] or 0
        L += [f"**{STAGE_VI[st]}: độ khớp từng trường** (model ở bảng trên, {n} {'creator' if st == 'screen' else 'video'}; "
              f"1 lần lệch ≈ {100 / n:.0f} điểm % của trường đó):" if n else f"**{STAGE_VI[st]}: độ khớp từng trường:**", "",
              "| Trường | " + " | ".join(f"{name}: {c['pick']['model']}" for name, c in rows) + " |",
              "|---|" + "---|" * len(rows)]
        for f in fields:
            L.append(f"| {FIELD_VI.get(f, f)} | " + " | ".join(_pct(c["pick"]["fields"].get(f)) for _, c in rows) + " |")
        L.append("")
    share = rec.get("provider_share") or []
    if share:
        L += ["**Tỷ lệ chi phí theo hãng trong phương án đề xuất (500 KOC):** "
              + " · ".join(f"{s['name']} {s['share']:.0%} (${s['usd_500_koc']:.2f})" for s in share) + "."
              + "".join(f" {p['name']} không được chọn ở bước nào (lý do từng bước ở bảng trên)."
                        for p in provs if p["name"] not in {s["name"] for s in share}), ""]
    return L


def render_recommendation(rec: dict) -> list[str]:
    names = {"screen": "Sàng lọc (text)", "video": "Xem video", "rationale": "Viết lý do"}
    L = ["## Đề xuất model cho từng bước", "",
         f"Luật: (1) chọn model **rẻ nhất** có độ khớp tham chiếu ≥ {rec['min_agreement']:.0%} và không lỗi; "
         "(2) **nâng cấp** lên model khớp cao hơn nếu hơn ≥ 5 điểm % mà chỉ tốn thêm ≤ $2 cho 500 KOC; "
         "(3) bước viết lý do: rẻ nhất có 100% trích dẫn hợp lệ. Vì chi phí nhân lên theo số KOC, model đắt chỉ đáng "
         "dùng khi chất lượng tăng tương xứng.", "",
         "| Bước | Đề xuất | Khớp tham chiếu | USD/item | USD cho 500 KOC | Độ trễ TB | Đang dùng | Lý do |",
         "|---|---|---|---|---|---|---|---|"]
    for st, v in rec["stages"].items():
        L.append(f"| {names[st]} | **{v['model']}** ({v['effort']}) | {_pct(v['agreement'])} | {v['usd_per_item']:.5f} | "
                 f"{v['usd_500_koc']:.2f} | {v['avg_latency_s']:.1f}s | {v['current']} | {v['why']} |")
    L += ["", "**Chi phí AI dự phóng cho 500 KOC** (theo tỷ lệ phễu thực tế của run):", "",
          "| Phương án | Sàng lọc | Xem video | Viết lý do | USD cho 500 KOC |", "|---|---|---|---|---|"]
    for p in rec["plans"]:
        r = p["routing"]
        cost = "–" if p["usd_500_koc"] is None else f"{p['usd_500_koc']:.2f}"
        L.append(f"| {p['name']} | {r.get('screen', '–')} | {r.get('video', '–')} | {r.get('rationale', '–')} | {cost} |")
    L += [""] + render_providers(rec)
    if rec.get("stability"):
        L += ["", "**Độ ổn định của bộ KOC** – mỗi KOC được bao nhiêu % biến thể chọn (mỗi biến thể dùng 1 model cho cả "
              "sàng lọc + xem video; phần định lượng giữ nguyên). KOC được ≥ 80% biến thể chọn là lựa chọn chắc chắn; "
              "thấp hơn là nhóm sát ngưỡng, kết quả phụ thuộc model:", "",
              f"| KOC | Tỷ lệ biến thể chọn | Có trong đề xuất của run `{rec.get('run_id', '?')}` (input benchmark) |",
              "|---|---|---|"]
        for s in rec["stability"]:
            L.append(f"| @{s['handle']} | {s['share']:.0%} | {'có' if s['in_pipeline'] else '–'} |")
    L += ["", "Lưu ý về độ chính xác: tham chiếu là đồng thuận của 3 model mạnh (chưa phải nhãn người). Model thuộc nhóm "
          "tham chiếu (Opus, Gemini 4 Carbon, DeepSeek V4 Pro) có lợi thế khi so ở effort thấp. Cột \"Khớp người\" có số "
          "sau khi người gán nhãn `eval/golden_labels.csv`.", ""]
    return L


def render_only(run_id: str | None = None):
    """Dựng lại benchmark_models.md (+ đề xuất) từ benchmark_models.json, không gọi model."""
    cfg = config.load_all()
    rep = json.loads((config.RESULTS_DIR / "benchmark_models.json").read_text(encoding="utf-8"))
    result = json.loads((config.RESULTS_DIR / rep["run_id"] / "result.json").read_text(encoding="utf-8"))
    b = cfg["models"]["benchmark"]
    rep["recommendation"] = recommend(rep, result, b, cfg["models"]["routing"], cfg["models"]["models"])
    rep.setdefault("total_cost_usd", sum(r["cost_usd"] for runs in rep["stages"].values() for r in runs))
    rep.setdefault("generated_at", time.strftime("%Y-%m-%d %H:%M",
                   time.localtime((config.RESULTS_DIR / "benchmark_models.json").stat().st_mtime)))
    (config.RESULTS_DIR / "benchmark_models.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (config.RESULTS_DIR / "benchmark_models.md").write_text(render(rep, result, b), encoding="utf-8")
    print(f"Đã dựng lại {config.RESULTS_DIR / 'benchmark_models.md'}")


def render(rep: dict, result: dict, b: dict) -> str:
    n_sel = max(1, len(result["choice"]["selected"]))
    f = result["funnel"]
    per_koc = {"screen": f["screened"] / n_sel, "video": f["video_analyzed"] / n_sel}
    L = [f"# Benchmark model – input của run `{rep['run_id']}`", "",
         f"> **Dữ liệu đã lưu (cache).** Benchmark chạy lúc {rep.get('generated_at', '?')}, tốn "
         f"${rep.get('total_cost_usd', 0):.2f} cho {sum(len(r) for r in rep['stages'].values())} biến thể "
         "(bước × model × effort). Đọc file này không gọi model, không cần API key. Chạy lại: "
         f"`uv run koc bench --run-id {rep['run_id']}` (cần key Anthropic, Gemini, DeepSeek; ~$2, ~40 phút).", ""]
    if rep.get("recommendation"):
        L += render_recommendation(rep["recommendation"])
    L += ["## Số liệu chi tiết", "",
         "Cùng input, đổi model. **Tham chiếu** = đồng thuận (đa số / trung vị) của "
         + ", ".join(b["reference_models"]) + f" ở effort `{b['reference_effort']}`. "
         f"Chi phí cho 500 KOC = chi phí mỗi item × số item phải xử lý cho mỗi KOC được chọn theo phễu thực tế "
         f"(screen {per_koc['screen']:.1f}, video {per_koc['video']:.1f} item/KOC). "
         "Claude và DeepSeek xem video qua 6 khung hình + phụ đề; Gemini xem video gốc có tiếng.", ""]
    if rep.get("skipped"):
        L += ["Bỏ qua: " + ", ".join(f"{m} ({why})" for m, why in rep["skipped"].items()), ""]
    for stage, runs in rep["stages"].items():
        L += [f"### {stage}", ""]
        if stage == "rationale":
            L += ["| Model | Effort | Thời gian (s) | Token vào | Token ra | USD | Trích dẫn hợp lệ | Độ dài lý do TB |",
                  "|---|---|---|---|---|---|---|---|"]
            for r in runs:
                cc = r.get("citation_check") or {}
                L.append(f"| {r['model']} | {r['effort']} | {r['seconds']} | {r['input_tokens']:,} | {r['output_tokens']:,} | "
                         f"{r['cost_usd']:.4f} | {_pct(cc.get('valid_rate'))} | {r.get('avg_reason_chars') or 0:.0f} |")
        else:
            n_items = len(result["screens"] if stage == "screen" else result["videos"])
            L += ["| Model | Effort | Lỗi | Thời gian (s) | Token vào | Token ra | USD | USD/item | USD cho 500 KOC | Khớp tham chiếu | MAE điểm | Khớp người |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|"]
            for r in sorted(runs, key=lambda r: r["cost_usd"]):
                a = r.get("agreement_vs_ref") or {}
                mae = ", ".join(f"{k[:-4]}={v:.1f}" for k, v in a.items() if k.endswith("_mae"))
                per_item = r["cost_usd"] / n_items if n_items else 0
                ref_mark = " *(ref)*" if r["model"] in b["reference_models"] and r["effort"] == b["reference_effort"] else ""
                L.append(f"| {r['model']}{ref_mark} | {r['effort']} | {len(r['errors'])} | {r['seconds']} | {r['input_tokens']:,} | "
                         f"{r['output_tokens']:,} | {r['cost_usd']:.4f} | {per_item:.5f} | {per_item * per_koc[stage] * 500:.2f} | "
                         f"{_pct(a.get('exact_avg'))} | {mae or '–'} | {_pct(r.get('agreement_vs_human'))} |")
        L.append("")
    L += ["### Bộ KOC có đổi theo model không?", "",
          "Nếu dùng cùng một model cho cả bước sàng lọc và bước video (phần định lượng giữ nguyên):", "",
          "| Model | Effort | KOC được chọn | Jaccard so với pipeline |", "|---|---|---|---|"]
    for t in rep["picks"]:
        L.append(f"| {t['model']} | {t['effort']} | {', '.join(t['selected']) or '–'} | {_pct(t['jaccard_vs_pipeline'])} |")
    L.append("")
    return "\n".join(L) + "\n"
