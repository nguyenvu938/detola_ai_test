"""Tải video TikTok, rút keyframe và phụ đề – chuẩn bị "gói bằng chứng" cho model.

- yt-dlp tải video công khai + phụ đề tự động của TikTok (nếu có).
- ffmpeg (bản đóng gói sẵn trong imageio-ffmpeg) rút vài khung hình nhỏ.
Model không xem được video (Claude) sẽ nhận: khung hình + phụ đề + mô tả.
Model xem được video (Gemini) nhận thẳng file mp4.
"""
import json
import re
import subprocess
import urllib.request
from pathlib import Path

import imageio_ffmpeg
import yt_dlp

from koc.config import DATA_DIR

VIDEO_DIR = DATA_DIR / "videos"


def is_on_topic(video: dict, keywords: list[str]) -> bool:
    """Đúng chủ đề nếu mô tả có từ khóa, HOẶC video lấy từ bảng xếp hạng theo danh mục của chiến dịch."""
    if video.get("source") == "video_rank_organic":
        return True
    return any(k in (video.get("description") or "").lower() for k in keywords)


def rank_videos(detail: dict, keywords: list[str]) -> list[dict]:
    """Thứ tự ưu tiên: đúng chủ đề kem chống nắng trước, không phải video quảng cáo trước
    (video chỉ chạy ads thường không xem công khai được), rồi nhiều view hơn."""
    videos = [v for v in (detail.get("videos") or []) if v.get("video_id")]
    return sorted(videos, key=lambda v: (not is_on_topic(v, keywords), bool(v.get("is_ad")), -(v.get("views") or 0)))


class VideoUnavailable(RuntimeError):
    pass


BASE_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "cachedir": False,          # không để yt-dlp ghi cache ra ổ C
    "retries": 3,
}
STAT_KEYS = ("view_count", "like_count", "comment_count", "save_count", "repost_count")


KALO_URLS = DATA_DIR / "kalodata" / "video_urls.json"   # video_id -> link mp4 do Kalodata cung cấp


def _http_get(url: str, out: Path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out.write_bytes(r.read())


def fetch_kalodata_videos(path: Path = KALO_URLS) -> dict:
    """Tải mp4 từ link Kalodata (link có chữ ký, hết hạn nhanh -> chạy ngay sau khi lấy link).
    Production: endpoint Kalodata API `POST /openapi/v1/tiktok/video/url`."""
    if not path.exists():
        return {"ok": 0, "failed": []}
    urls = json.loads(path.read_text(encoding="utf-8"))
    ok, failed = 0, []
    for vid, url in urls.items():
        mp4 = VIDEO_DIR / vid / f"{vid}.mp4"
        if mp4.exists():
            ok += 1
            continue
        mp4.parent.mkdir(parents=True, exist_ok=True)
        try:
            _http_get(url, mp4)
            ok += 1
        except Exception as e:
            mp4.unlink(missing_ok=True)
            failed.append(f"{vid}: {str(e)[:80]}")
    return {"ok": ok, "failed": failed}


def download(video: dict) -> dict:
    """Lấy 1 bài TikTok vào data/videos/<id>/ (đã có thì dùng lại).

    - Có file mp4 (tải bằng yt-dlp hoặc từ link Kalodata) -> {"kind": "video", "mp4", "subtitle"}
    - TikTok không trả luồng video -> {"kind": "no_stream", "cover", "audio"}.
      Khi xem không đăng nhập, TikTok giấu link video của bài gắn giỏ hàng/quảng cáo (playAddr trống);
      bài ảnh (slideshow) cũng không có luồng video. Khi đó chỉ còn ảnh bìa + âm thanh.
    Kèm "stats": like/comment/save/view công khai của bài.
    """
    vid = video["video_id"]
    out_dir = VIDEO_DIR / vid
    out_dir.mkdir(parents=True, exist_ok=True)
    mp4 = out_dir / f"{vid}.mp4"
    meta_path = out_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else None
    if meta and meta.get("kind") == "photo":     # nhãn cũ (đoán nhầm là bài ảnh) -> gọi đúng tên
        meta["kind"] = "no_stream"

    if mp4.exists():
        subs = sorted(out_dir.glob("*.vtt")) + sorted(out_dir.glob("*.srt"))
        return {**(meta or {}), "kind": "video", "mp4": mp4, "subtitle": subs[0] if subs else None}

    if meta is None:
        try:
            with yt_dlp.YoutubeDL(BASE_OPTS) as ydl:
                info = ydl.extract_info(video["url"], download=False)
        except Exception as e:   # bài đã xóa, riêng tư, TikTok tạm lỗi 5xx...
            raise VideoUnavailable(str(e)[:200]) from e
        has_video = any((f.get("vcodec") or "none") != "none" for f in info.get("formats") or [])
        meta = {
            "kind": "video" if has_video else "no_stream",
            "duration": info.get("duration"),
            "track": info.get("track"),
            "cover_url": next((t["url"] for t in info.get("thumbnails") or [] if t.get("id") == "originCover"),
                              info.get("thumbnail")),
            "stats": {k: info.get(k) for k in STAT_KEYS},
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    if meta["kind"] == "video":
        if not mp4.exists():
            opts = {
                **BASE_OPTS,
                "outtmpl": str(out_dir / f"{vid}.%(ext)s"),
                "format": "best[height<=720][vcodec!=none][acodec!=none]/best[vcodec!=none]",  # <=720p cho nhẹ
                "merge_output_format": "mp4",
                "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["vie.*", "vi.*"],
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([video["url"]])
            except yt_dlp.utils.DownloadError as e:
                raise VideoUnavailable(str(e)[:200]) from e
        subs = sorted(out_dir.glob("*.vtt")) + sorted(out_dir.glob("*.srt"))
        return {**meta, "mp4": mp4, "subtitle": subs[0] if subs else None}

    # Không có luồng video: ảnh bìa (thu nhỏ bằng ffmpeg) + âm thanh của bài
    cover = out_dir / "cover_384.jpg"
    if not cover.exists() and meta.get("cover_url"):
        raw = out_dir / "cover_raw"
        try:
            with yt_dlp.YoutubeDL(BASE_OPTS) as ydl:
                raw.write_bytes(ydl.urlopen(meta["cover_url"]).read())
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(raw),
                            "-vf", "scale=384:-2", "-q:v", "5", str(cover)], check=True)
        except Exception:
            # link ảnh bìa TikTok có chữ ký, hết hạn sau vài giờ -> xóa meta để lần sau lấy link mới
            meta_path.unlink(missing_ok=True)
    audio = out_dir / f"{vid}.mp3"
    if not audio.exists():
        try:
            with yt_dlp.YoutubeDL({**BASE_OPTS, "outtmpl": str(out_dir / f"{vid}.%(ext)s"), "format": "audio"}) as ydl:
                ydl.download([video["url"]])
        except Exception:
            pass   # thiếu âm thanh thì vẫn phân tích được bằng ảnh bìa + mô tả
    return {**meta, "cover": cover if cover.exists() else None, "audio": audio if audio.exists() else None}


def subtitle_text(path: Path | None, max_chars: int = 1500) -> str:
    """Đổi VTT/SRT sang văn bản thường, bỏ mốc giờ và dòng trùng."""
    if not path:
        return ""
    lines, seen = [], set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or "-->" in line or line.isdigit() or line.startswith(("WEBVTT", "NOTE")):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return " ".join(lines)[:max_chars]


def duration_seconds(mp4: Path) -> float:
    _, secs = imageio_ffmpeg.count_frames_and_secs(str(mp4))
    return secs


def extract_frames(mp4: Path, n: int, width: int, clip_seconds: int) -> list[tuple[float, Path]]:
    """Rút n khung: 2 khung ở 3 giây đầu (hook) + phần còn lại rải đều trong đoạn clip."""
    dur = min(duration_seconds(mp4), clip_seconds)
    times = [0.5, 2.5] + [dur * (i + 1) / (n - 1) for i in range(n - 2)]
    times = sorted({round(min(t, max(dur - 0.5, 0)), 1) for t in times})
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    frames = []
    for t in times:
        out = mp4.parent / f"frame_{t:05.1f}_{width}.jpg"
        if not out.exists():
            subprocess.run(
                [ffmpeg, "-y", "-loglevel", "error", "-ss", str(t), "-i", str(mp4),
                 "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "5", str(out)],
                check=True,
            )
        frames.append((t, out))
    return frames
