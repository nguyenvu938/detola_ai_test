"""Adapter Gemini (google-genai SDK). Gemini xem được video gốc kèm âm thanh.

Tiết kiệm token video: media_resolution LOW (~66 token/khung thay vì 258),
chỉ cắt 60 giây đầu (end_offset), 1 khung/giây. ~100 token/giây video có tiếng.
"""
import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import types

from koc.llm.base import CallFailed

INLINE_LIMIT = 18 * 1024 * 1024   # request inline tối đa ~20MB
UPLOAD_TIMEOUT_S = 120            # file lớn phải upload: chờ Gemini xử lý tối đa 2 phút

# effort của dự án -> mức suy nghĩ (thinking_level) của Gemini. Không có effort thì để Gemini tự chọn.
THINKING_LEVEL = {"minimal": "MINIMAL", "low": "LOW", "medium": "MEDIUM", "high": "HIGH", "xhigh": "XHIGH", "max": "XHIGH"}
# Token suy nghĩ tính CHUNG vào max_output_tokens: không chừa chỗ thì mức high nghĩ hết giới hạn, chưa kịp viết JSON
# (đo được: Gemini 4 Carbon high dùng trọn 6.000 token ở bước sàng lọc mà không ra kết quả).
# Chỉ trả tiền cho token thực dùng, nên chừa rộng không tốn thêm.
THINKING_HEADROOM = {"minimal": 0, "low": 4000, "medium": 8000, "high": 16000, "xhigh": 32000, "max": 32000}
AUDIO_MIME = {".mp3": "audio/mp3", ".wav": "audio/wav", ".aac": "audio/aac", ".ogg": "audio/ogg", ".flac": "audio/flac"}


def thinking_config(effort: str | None) -> types.ThinkingConfig | None:
    return types.ThinkingConfig(thinking_level=THINKING_LEVEL[effort]) if effort else None


def cost_usd(usage, model_cfg: dict) -> float:
    """Giá theo loại token: token âm thanh có giá riêng ở một số model (vd 3.1 Flash-Lite: 0.50 thay vì 0.25/1M).
    Token suy nghĩ (thoughts) tính giá token ra."""
    in_tok = usage.prompt_token_count or 0
    audio = sum(d.token_count or 0 for d in (usage.prompt_tokens_details or [])
                if d.modality is not None and d.modality.name == "AUDIO")
    out_tok = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
    audio_price = model_cfg.get("audio_input_per_m", model_cfg["input_per_m"])
    return ((in_tok - audio) * model_cfg["input_per_m"] + audio * audio_price
            + out_tok * model_cfg["output_per_m"]) / 1_000_000


class GeminiAdapter:
    def __init__(self):
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Chưa có GEMINI_API_KEY trong .env")
        self.client = genai.Client(api_key=key)

    def _video_part(self, path: Path, clip_seconds: int, uploaded: list) -> types.Part:
        meta = types.VideoMetadata(start_offset="0s", end_offset=f"{clip_seconds}s", fps=1)
        if path.stat().st_size <= INLINE_LIMIT:
            return types.Part(inline_data=types.Blob(data=path.read_bytes(), mime_type="video/mp4"), video_metadata=meta)
        f = self.client.files.upload(file=str(path))
        uploaded.append(f.name)            # xoá sau khi phân tích, không để đầy kho lưu file của Gemini
        deadline = time.monotonic() + UPLOAD_TIMEOUT_S
        while f.state is None or f.state.name != "ACTIVE":
            if f.state and f.state.name == "FAILED":
                raise RuntimeError("Gemini xử lý file video thất bại")
            if time.monotonic() > deadline:
                raise RuntimeError(f"Gemini xử lý file video quá {UPLOAD_TIMEOUT_S}s")
            time.sleep(3)
            f = self.client.files.get(name=f.name)
        return types.Part(file_data=types.FileData(file_uri=f.uri, mime_type=f.mime_type), video_metadata=meta)

    def complete(self, *, model, system, parts, schema, effort, max_tokens, model_cfg):
        uploaded: list[str] = []
        try:
            return self._complete(model, system, parts, schema, effort, max_tokens, model_cfg, uploaded)
        finally:
            for name in uploaded:
                try:
                    self.client.files.delete(name=name)
                except Exception:
                    pass   # Gemini tự xoá file sau 48 giờ

    def _complete(self, model, system, parts, schema, effort, max_tokens, model_cfg, uploaded):
        g_parts = []
        for p in parts:
            if p["type"] == "text":
                g_parts.append(types.Part.from_text(text=p["text"]))
            elif p["type"] == "image":
                g_parts.append(types.Part.from_bytes(data=Path(p["path"]).read_bytes(), mime_type="image/jpeg"))
            elif p["type"] == "video":
                g_parts.append(self._video_part(Path(p["path"]), p.get("clip_seconds", 60), uploaded))
            elif p["type"] == "audio":
                path = Path(p["path"])
                g_parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=AUDIO_MIME[path.suffix.lower()]))
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
            max_output_tokens=max_tokens + THINKING_HEADROOM.get(effort, 0),
            thinking_config=thinking_config(effort),
        )
        resp = self.client.models.generate_content(
            model=model, contents=[types.Content(role="user", parts=g_parts)], config=config
        )
        u = resp.usage_metadata
        in_tok = u.prompt_token_count or 0
        out_tok = (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
        cost = cost_usd(u, model_cfg)
        try:
            data = resp.parsed.model_dump() if resp.parsed is not None else schema.model_validate(json.loads(resp.text)).model_dump()
        except Exception as e:   # hết token ra, bị chặn, JSON hỏng: vẫn bị tính tiền
            raise CallFailed(f"Gemini không trả JSON hợp lệ: {str(e)[:200]}", in_tok, out_tok, cost) from e
        return data, in_tok, out_tok, cost
