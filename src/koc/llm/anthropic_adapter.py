"""Adapter Claude (Anthropic SDK). Dùng structured output: SDK kiểm JSON theo schema Pydantic."""
import base64
from pathlib import Path

import anthropic


class AnthropicAdapter:
    def __init__(self):
        # Key đọc từ biến môi trường ANTHROPIC_API_KEY (nạp từ .env bằng python-dotenv ở cli.py)
        self.client = anthropic.Anthropic(max_retries=3)

    @staticmethod
    def _content(parts: list[dict]) -> list[dict]:
        out = []
        for p in parts:
            if p["type"] == "text":
                out.append({"type": "text", "text": p["text"]})
            elif p["type"] == "image":
                data = base64.standard_b64encode(Path(p["path"]).read_bytes()).decode()
                out.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}})
            else:
                raise ValueError(f"Claude không nhận trực tiếp '{p['type']}' – hãy tách keyframe trước")
        return out

    def complete(self, *, model, system, parts, schema, effort, max_tokens, model_cfg):
        kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            # system prompt cố định -> đặt cache_control để các lần gọi sau đọc từ cache (rẻ ~10 lần)
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": self._content(parts)}],
            output_format=schema,
        )
        if effort:
            kwargs["output_config"] = {"effort": effort}
        resp = self.client.messages.parse(**kwargs)

        if resp.stop_reason == "refusal":
            raise RuntimeError(f"Model từ chối: {resp.stop_details}")
        if resp.stop_reason == "max_tokens":
            raise RuntimeError("Hết max_tokens trước khi xong JSON")
        if resp.parsed_output is None:
            raise RuntimeError("Không đọc được JSON theo schema")

        u = resp.usage
        cache_write = u.cache_creation_input_tokens or 0
        cache_read = u.cache_read_input_tokens or 0
        in_tok = u.input_tokens + cache_write + cache_read
        # Giá: ghi cache ×1.25, đọc cache ×0.1 so với input thường
        cost = ((u.input_tokens + 1.25 * cache_write + 0.1 * cache_read) * model_cfg["input_per_m"]
                + u.output_tokens * model_cfg["output_per_m"]) / 1_000_000
        return resp.parsed_output.model_dump(), in_tok, u.output_tokens, cost
