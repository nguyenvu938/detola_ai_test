"""Ghi kết quả 1 run: results/<run_id>/recommendation.md + result.json."""
import json

from koc.sources.kalodata import REVENUE_BASIS

from koc.config import RESULTS_DIR

VND = lambda x: f"{x / 1e6:,.1f} tr"  # noqa: E731


def write(result: dict, routing: dict, total_seconds: float) -> dict:
    out_dir = RESULTS_DIR / result["run_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md = render(result, routing, total_seconds)
    (out_dir / "recommendation.md").write_text(md, encoding="utf-8")
    return {"dir": out_dir, "markdown": md}


def render(r: dict, routing: dict, total_seconds: float) -> str:
    product = (r.get("campaign") or {}).get("product", "sản phẩm")
    choice, final = r["choice"], r.get("final") or {}
    rat = {k["handle"]: k for k in (final.get("rationale") or {}).get("kocs", [])}
    L = [f"# Đề xuất KOC – run `{r['run_id']}`", "",
         f"> **Dữ liệu đã lưu (cache).** Run chạy lúc {r.get('generated_at', '?')} với "
         + ", ".join(f"{k}={v}" for k, v in (r.get("routing") or {}).items())
         + f"; {r.get('llm_calls', '?')} lần gọi model, chi phí ${r['cost_usd']:.4f}. Đọc file này không gọi model. "
         f"Chạy lại: `uv run koc run --run-id {r['run_id']}` (cần GEMINI_API_KEY; chỉ có ANTHROPIC_API_KEY thì mọi "
         "bước tự dùng Claude Haiku).", ""]
    f = r["funnel"]
    L += ["## Phễu xử lý", "",
          f"{f.get('ingested')} creator (gộp các danh sách Kalodata) → lọc luật {f.get('after_prefilter')} "
          f"→ lấy chi tiết {f.get('enriched_target')} → đạt khán giả/loại tài khoản {f.get('after_metrics')} "
          f"→ LLM sàng lọc {f.get('screened')} (đạt cổng {f.get('passed_screen_gate')}) → phân tích video "
          f"{f.get('video_analyzed')} → đạt ngưỡng điểm {f.get('above_min_score')} → **chọn {f.get('selected')}**", ""]
    if final.get("rationale"):
        L += ["## Tóm tắt", "", final["rationale"]["summary_vi"], ""]
    L += ["## 5 KOC đề xuất", "",
          "| # | KOC | Follower | Khán giả mục tiêu | Doanh thu 30 ngày (cơ sở) | Điểm | Chi phí ước tính |",
          "|---|---|---|---|---|---|---|"]
    for i, s in enumerate(choice["selected"], 1):
        tgt = f"{s['target_share']:.0%}" if s.get("target_share") is not None else s.get("audience_source", "–")
        L.append(f"| {i} | [@{s['handle']}](https://www.tiktok.com/@{s['handle']}) | {s['followers']:,} | {tgt} | "
                 f"{VND(s['category_gmv_vnd'])} ({REVENUE_BASIS.get(s.get('gmv_basis'), '?').format(product=product)}) | "
                 f"{s['final_score']:.3f} | {VND(s['est_cost_vnd'])} |")
    ads = choice.get("ads_reserve_vnd", 0)
    L += ["", f"Chi phí ước tính = phí review + phí cấp mã Spark Ads theo tier follower (`config/market.toml`). "
          f"Tổng booking **{VND(choice['total_cost_vnd'])}**, còn **{VND(ads)}** để chạy Spark Ads cho 2–3 video tốt nhất "
          f"sau 48 giờ (khuyến nghị {VND(choice.get('recommended_ads_vnd', 0))}). Hoa hồng affiliate 12–18% tính "
          "trên doanh số, không nằm trong ngân sách cố định.", ""]
    if choice.get("ads_note"):
        L += [f"> {choice['ads_note']}", ""]
    if choice.get("note"):
        L += [f"> {choice['note']}", ""]
    if choice.get("below_threshold"):
        L += ["Đã phân tích video nhưng dưới ngưỡng điểm: " + ", ".join(
            f"@{b['handle']} ({b['final_score']:.2f})" for b in choice["below_threshold"]), ""]

    for s in choice["selected"]:
        h = s["handle"]
        v = r["videos"][h]
        a = v["analysis"]
        k = rat.get(h, {})
        L += [f"### @{h}", ""]
        if k:
            L += [k["reason_vi"], "", f"- **Rủi ro:** {k['risks_vi']}", f"- **Gợi ý brief:** {k['brief_suggestion_vi']}"]
        L += [f"- **Điểm thành phần:** định lượng {s['metric_score']:.2f}, sàng lọc {s['screen_score']:.2f}, video {s['video_score']:.2f} "
              f"({', '.join(f'{x}={y}' for x, y in s['metric_parts'].items())})",
              f"- **{'Video' if v.get('kind') == 'video' else 'Bài (chỉ ảnh bìa)'} đã phân tích** ({v['input']['mode']}): "
              f"[{v['video_id']}]({v['url']}) – {a['summary_vi']}"]
        for e in a["evidence"]:
            L.append(f"  - `{e['at']}` {e['observation']}")
        if k.get("evidence_refs"):
            L.append(f"- Bằng chứng trích dẫn: {', '.join(k['evidence_refs'])}")
        L.append("")

    cc = final.get("citation_check")
    if cc:
        L += [f"Kiểm tra trích dẫn bằng code: {cc['refs_total']} mã, sai {len(cc['refs_invalid'])}, "
              f"khớp danh sách KOC: {cc['handles_match']}.", ""]

    reg = f.get("registry")
    if reg:
        L += ["## So với lần quét trước", "",
              f"Mới {reg['new']} · thay đổi {reg['changed']} · không đổi {reg['unchanged']} · quá hạn {reg['stale']} "
              "(sổ đăng ký creator, `koc changes`). Creator không đổi được dùng lại kết quả phân tích cũ; chỉ phần mới "
              "(video mới, hồ sơ đổi) mới gọi model.", ""]
        for c in [x for x in r.get("registry_changes", []) if x["status"] in ("changed", "stale")][:15]:
            L.append(f"- @{c['handle']} ({c['status']}): {', '.join(c['changes'])}")
        L.append("")
    saved = sum(u.get("saved_usd") or 0 for u in r["usage"])
    L += ["## Chi phí AI và thời gian", "",
          "| Stage | Model | Lần gọi | Dùng lại kết quả cũ | Token vào | Token ra | USD | Tiết kiệm nhờ dùng lại | Độ trễ TB (ms) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for u in r["usage"]:
        L.append(f"| {u['stage']} | {u['model']} | {u['calls']} | {u['cache_hits']} | {u['input_tokens']:,} | "
                 f"{u['output_tokens']:,} | {u['cost_usd']:.4f} | {u.get('saved_usd') or 0:.4f} | {u['avg_latency_ms']:.0f} |")
    if saved:
        L += ["", f"Dùng lại kết quả phân tích từ các lần quét trước tiết kiệm **${saved:.4f}** trong run này."]
    L += ["", f"**Tổng chi phí AI: ${r['cost_usd']:.4f}** "
          f"(≈ {r['cost_usd'] * 26_000:,.0f} VNĐ, tỷ giá tham khảo 26.000).", ""]
    L += ["| Stage | Thời gian xử lý cộng dồn (s) |", "|---|---|"]
    for t in r["timings"]:
        L.append(f"| {t['stage']} | {t['seconds']:.1f} |")
    tot_s = sum(t["seconds"] for t in r["timings"])
    tok_in = sum(u["input_tokens"] for u in r["usage"])
    tok_out = sum(u["output_tokens"] for u in r["usage"])
    L += ["", f"**Tổng thời gian xử lý: {tot_s:.0f} giây** (cộng các stage qua mọi lần chạy/resume; lần chạy cuối "
          f"mất {total_seconds:.1f}s). **Token: {tok_in:,} vào / {tok_out:,} ra.**", "",
          "Định tuyến model: " + ", ".join(f"{k}={v['model']}" for k, v in routing.items()), ""]

    L += ["## Ứng viên bị loại ở các bước sau (trích)", ""]
    for d in r["dropped"]["metrics"][:10]:
        L.append(f"- @{d['handle']}: {d['reason']}")
    for h, s in r["screens"].items():
        if s["account_kind"] in ("brand_official", "shop_seller"):
            L.append(f"- @{h}: LLM phân loại là {s['account_kind']} – {s['fit_note']}")
    return "\n".join(L) + "\n"
