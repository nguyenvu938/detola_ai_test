"""Stage 5 – phân tích video bằng AI, chỉ cho top-K ứng viên (bước đắt nhất nên làm ít nhất)."""
from koc import media
from koc.config import load_prompt, prompt_vars
from koc.schemas import VideoAnalysis

PROMPT_FILE = "video_v2.txt"   # v2: brief lấy từ campaign.toml, xử lý cả bài không xem được hình


def fetch_first_available(detail: dict, keywords: list[str], max_tries: int = 10) -> tuple[dict, dict, list[str]]:
    """Thử các bài theo thứ tự ưu tiên, lấy bài đầu tiên có VIDEO. Không có thì dùng bài không-luồng-video đầu tiên.
    Trả (bài, file đã tải, ghi chú các bài bị bỏ qua). Mỗi lần thử chỉ đọc metadata (~2s), chưa tải file."""
    skipped, fallback = [], None
    for post in media.rank_videos(detail, keywords)[:max_tries]:
        try:
            files = media.download(post)
        except media.VideoUnavailable as e:
            skipped.append(f"{post['video_id']}: không tải được ({e})")
            continue
        if files["kind"] == "video":
            return post, files, skipped
        skipped.append(f"{post['video_id']}: không có luồng video")
        fallback = fallback or (post, files)
    if fallback:
        return fallback[0], fallback[1], skipped
    raise RuntimeError(f"Không tải được bài nào ({len(skipped)} lần thử): {skipped}")


def build_parts(post: dict, files: dict, route: dict, model_cfg: dict) -> tuple[list[dict], dict]:
    # Chỉ đưa nội dung KHÔNG đổi theo thời gian (mô tả, thời lượng). Lượt xem/like đổi hằng ngày mà không làm
    # nội dung video khác đi -> để ngoài input, nhờ vậy video đã phân tích được dùng lại mãi (theo ID video).
    header = (f"Mô tả bài: {post.get('description') or ''}\n"
              f"Thời lượng: {post.get('duration_s')}s")
    can_video, can_audio = model_cfg.get("video", False), model_cfg.get("audio", False)

    if files["kind"] != "video":
        text = header + ("\nKhông xem được hình động của bài này (TikTok không cung cấp luồng video: thường là video "
                         "gắn giỏ hàng/quảng cáo, hoặc bài ảnh). Ảnh đính kèm là ẢNH BÌA; chỉ đánh giá điều thấy trong "
                         "ảnh bìa, mô tả và âm thanh (nếu có).")
        parts = [{"type": "text", "text": text}]
        if files.get("cover"):
            parts.append({"type": "image", "path": str(files["cover"])})
        if can_audio and files.get("audio"):
            parts.append({"type": "audio", "path": str(files["audio"])})
            parts[0]["text"] += f"\nĐính kèm âm thanh của bài ({files.get('track')})."
        else:
            parts[0]["text"] += "\n(Model không nghe được âm thanh của bài.)"
        return parts, {"mode": "cover_only", "audio": bool(can_audio and files.get("audio"))}

    if can_video:
        parts = [{"type": "text", "text": header},
                 {"type": "video", "path": str(files["mp4"]), "clip_seconds": route.get("clip_seconds", 60)}]
        return parts, {"mode": "native_video"}

    transcript = media.subtitle_text(files["subtitle"])
    frames = media.extract_frames(files["mp4"], route.get("frames", 6), route.get("frame_width", 384),
                                  route.get("clip_seconds", 60))
    text = header + f"\nPhụ đề/lời thoại: {transcript or '(không có phụ đề)'}\n"
    text += "Các khung hình theo thứ tự: " + ", ".join(f"frame {i + 1} @ {t:.1f}s" for i, (t, _) in enumerate(frames))
    parts = [{"type": "text", "text": text}] + [{"type": "image", "path": str(p)} for _, p in frames]
    return parts, {"mode": "keyframes", "frames": len(frames), "has_transcript": bool(transcript)}


def analyze_creator(llm, detail: dict, campaign: dict, route: dict, model_cfg: dict) -> dict:
    keywords = campaign["topic_keywords"]
    post, files, skipped = fetch_first_available(detail, keywords)
    out = analyze_video(llm, detail["handle"], post, files, route, model_cfg, campaign)
    out["on_topic_by_title"] = media.is_on_topic(post, keywords)
    out["input"]["skipped_posts"] = skipped
    # Bài ảnh dự phòng đã nằm trong skipped, nên chỉ cộng thêm khi bài được chọn là video.
    checked = len(skipped) + (files["kind"] == "video")
    no_stream = sum("không có luồng video" in s for s in skipped)
    out["format_mix"] = {"checked": checked, "no_stream_posts": no_stream}   # bao nhiêu bài không xem được hình
    return out


def analyze_video(llm, handle: str, post: dict, files: dict, route: dict, model_cfg: dict, campaign: dict) -> dict:
    """Phân tích 1 bài cụ thể (benchmark dùng hàm này để mọi model xem cùng 1 bài)."""
    parts, meta = build_parts(post, files, route, model_cfg)
    res = llm.call(
        stage="video",
        model=route["model"],
        effort=route.get("effort"),
        system=load_prompt(PROMPT_FILE, **prompt_vars(campaign)),
        parts=parts,
        schema=VideoAnalysis,
        item_ids=[handle],
        max_tokens=3000,
    )
    return {
        "video_id": post["video_id"],
        "url": post["url"],
        "kind": files["kind"],
        "description": post.get("description"),
        "views": post.get("views"),
        "stats": files.get("stats"),
        "input": meta,
        "analysis": res.data,
    }
