"""Stage 7 – LLM viết lý do đề xuất cho bộ KOC đã chọn (1 lần gọi / 10 KOC), rồi code kiểm tra trích dẫn."""
import json
from concurrent.futures import ThreadPoolExecutor

from koc.audience import Target
from koc.config import load_prompt, prompt_vars
from koc.sources.kalodata import REVENUE_BASIS
from koc.schemas import RationaleSet

PROMPT_FILE = "rationale_v2.txt"   # v2: brief lấy từ campaign.toml


def evidence_pack(row: dict, screen: dict, video: dict, campaign: dict) -> dict:
    """Gom bằng chứng của 1 KOC, mỗi mục có mã để LLM trích dẫn và code kiểm lại."""
    target = Target(campaign).describe()
    product = campaign["product"]
    ev = {
        "M:audience": f"follower đúng giới mục tiêu {row['target_gender_share']:.0%}, ước tính {target} {row['target_share']:.0%}"
        if row.get("target_share") is not None else f"khán giả ({target}): {row.get('audience_source') or 'không rõ'}",
        "M:gmv": (f"doanh thu 30 ngày (Kalodata, {REVENUE_BASIS.get(row.get('gmv_basis'), '?').format(product=product)}) "
                  f"≈ {row['category_gmv_vnd'] / 1e6:,.0f} triệu VNĐ"),
        "M:engagement": f"engagement rate {row['engagement_rate']:.2%}" if row.get("engagement_rate") else "chưa có engagement rate",
        "M:organic": f"{(1 - row['ad_share']):.0%} lượt xem không đến từ quảng cáo" if row.get("ad_share") is not None else "không rõ",
        "S:screen": f"{screen['account_kind']}, ngách {screen['primary_niche']}, liên quan {product} {screen['topic_relevance']}/10; {screen['fit_note']}",
    }
    if row.get("reach_flag"):
        ev["M:reach"] = "cảnh báo: " + row["reach_flag"]
    if screen.get("competitor_brands"):
        ev["S:competitors"] = "đã quảng bá: " + ", ".join(screen["competitor_brands"])
    mix = video.get("format_mix")
    if mix:
        ev["V:format"] = (f"{mix['no_stream_posts']}/{mix['checked']} bài đã kiểm không xem được hình (video gắn giỏ/"
                          f"quảng cáo hoặc bài ảnh); bài được phân tích: "
                          f"{'video đầy đủ' if video.get('kind') == 'video' else 'chỉ ảnh bìa'}")
    a = video["analysis"]
    ev[f"V:{video['video_id']}"] = a["summary_vi"] + " | " + "; ".join(f"{e['at']}: {e['observation']}" for e in a["evidence"])
    return {
        "handle": row["handle"],
        "followers": row["followers"],
        "est_cost_vnd": row["est_cost_vnd"],
        "final_score": row["final_score"],
        "evidence": ev,
    }


def _write_chunk(llm, packs: list[dict], route: dict, campaign: dict) -> dict:
    res = llm.call(
        stage="rationale",
        model=route["model"],
        effort=route.get("effort"),
        system=load_prompt(PROMPT_FILE, **prompt_vars(campaign)),
        parts=[{"type": "text", "text": json.dumps(packs, ensure_ascii=False)}],
        schema=RationaleSet,
        item_ids=[p["handle"] for p in packs],
        max_tokens=8000,
    )
    return res.data


def write_rationale(llm, selected: list[dict], screens: dict, videos: dict, route: dict, campaign: dict,
                    concurrency: int = 1) -> dict:
    """Bộ nhỏ (<= batch_size KOC): 1 lần gọi. Bộ lớn (50–500 KOC): chia lô batch_size KOC/lần gọi, chạy song song.
    Lý do chia lô: 500 KOC × ~300 token lời giải thích vượt giới hạn token ra của 1 lần gọi."""
    packs = [evidence_pack(r, screens[r["handle"]], videos[r["handle"]], campaign) for r in selected]
    size = route.get("batch_size", 10)
    chunks = [packs[i:i + size] for i in range(0, len(packs), size)]
    with ThreadPoolExecutor(max_workers=max(1, min(concurrency, len(chunks)))) as ex:
        outs = list(ex.map(lambda c: _write_chunk(llm, c, route, campaign), chunks))
    if len(outs) == 1:
        data = outs[0]
    else:    # tóm tắt từng lô, ghi rõ lô nào gồm KOC nào
        data = {"summary_vi": "\n".join(f"Nhóm {i + 1} (@{c[0]['handle']} … @{c[-1]['handle']}): {o['summary_vi']}"
                                        for i, (c, o) in enumerate(zip(chunks, outs))),
                "kocs": [k for o in outs for k in o["kocs"]]}
    return {"packs": packs, "rationale": data, "citation_check": check_citations(data, packs)}


def check_citations(rationale: dict, packs: list[dict]) -> dict:
    """Kiểm bằng code: mọi mã bằng chứng LLM trích phải có thật trong input của đúng KOC đó."""
    valid = {p["handle"]: set(p["evidence"]) for p in packs}
    total, bad = 0, []
    for k in rationale["kocs"]:
        for ref in k["evidence_refs"]:
            total += 1
            if ref not in valid.get(k["handle"], set()):
                bad.append(f"{k['handle']}:{ref}")
    handles_ok = sorted(k["handle"] for k in rationale["kocs"]) == sorted(valid)
    return {"refs_total": total, "refs_invalid": bad, "valid_rate": (1 - len(bad) / total) if total else 0.0,
            "handles_match": handles_ok}
