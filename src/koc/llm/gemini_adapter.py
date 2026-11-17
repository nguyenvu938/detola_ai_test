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

INLINE_LIMIT = 18 * 1024 * 1024   # request inline tối đa ~20MB


class GeminiAdapter:
    def __init__(self):
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Chưa có GEMINI_API_KEY trong .env")
        self.client = genai.Client(api_key=key)

    def _video_part(self, path: Path, clip_seconds: int) -> types.Part:
        meta = types.VideoMetadata(start_offset="0s", end_offset=f"{clip_seconds}s", fps=1)
        if path.stat().st_size <= INLINE_LIMIT:
            return types.Part(inline_data=types.Blob(data=path.read_bytes(), mime_type="video/mp4"), video_metadata=meta)
        f = self.client.files.upload(file=str(path))
        while f.state is None or f.state.name != "ACTIVE":
            if f.state and f.state.name == "FAILED":
                raise RuntimeError("Gemini xử lý file video thất bại")
            time.sleep(3)
            f = self.client.files.get(name=f.name)
        return types.Part(file_data=types.FileData(file_uri=f.uri, mime_type=f.mime_type), video_metadata=meta)

    def complete(self, *, model, system, parts, schema, effort, max_tokens, model_cfg):
        g_parts = []
        for p in parts:
            if p["type"] == "text":
                g_parts.append(types.Part.from_text(text=p["text"]))
            elif p["type"] == "image":
                g_parts.append(types.Part.from_bytes(data=Path(p["path"]).read_bytes(), mime_type="image/jpeg"))
            elif p["type"] == "video":
                g_parts.append(self._video_part(Path(p["path"]), p.get("clip_seconds", 60)))
            elif p["type"] == "audio":
                g_parts.append(types.Part.from_bytes(data=Path(p["path"]).read_bytes(), mime_type="audio/mp3"))
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
            max_output_tokens=max_tokens,
        )
        resp = self.client.models.generate_content(
            model=model, contents=[types.Content(role="user", parts=g_parts)], config=config
        )
        data = resp.parsed.model_dump() if resp.parsed is not None else schema.model_validate(json.loads(resp.text)).model_dump()
        u = resp.usage_metadata
        in_tok = u.prompt_token_count or 0
        out_tok = (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
        return data, in_tok, out_tok, None
