"""Đọc cấu hình TOML (campaign, models, market). Dùng tomllib có sẵn trong Python 3.11+."""
import hashlib
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
PROMPT_DIR = ROOT / "prompts"
RESULTS_DIR = ROOT / "results"
STATE_DIR = ROOT / "state"


def load_toml(name: str) -> dict:
    with open(CONFIG_DIR / name, "rb") as f:
        return tomllib.load(f)


def load_all() -> dict:
    return {
        "campaign": load_toml("campaign.toml"),
        "models": load_toml("models.toml"),
        "market": load_toml("market.toml"),
    }


KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY", "deepseek": "DEEPSEEK_API_KEY"}


def apply_fallbacks(models_cfg: dict, env: dict) -> list[str]:
    """Bước nào có model chính thiếu API key mà có `fallback` thì chuyển sang fallback. Trả danh sách thông báo."""
    notes = []
    for stage, route in models_cfg["routing"].items():
        provider = models_cfg["models"][route["model"]]["provider"]
        if not env.get(KEY_ENV[provider]) and route.get("fallback"):
            notes.append(f"{stage}: thiếu {KEY_ENV[provider]} -> dùng {route['fallback']} thay {route['model']}")
            route["model"] = route["fallback"]
    return notes


def load_prompt(name: str, **variables) -> str:
    """Đọc prompt; nếu có biến thì điền vào chỗ {ten_bien} (brief chiến dịch, ngân sách...)."""
    text = (PROMPT_DIR / name).read_text(encoding="utf-8")
    return text.format(**variables) if variables else text


def prompt_vars(campaign: dict) -> dict:
    """Biến dùng chung cho mọi prompt, lấy từ [campaign] trong campaign.toml."""
    from koc.audience import Target
    return {
        "market": campaign.get("market", "Việt Nam"),
        "product": campaign["product"],
        "product_scope": campaign.get("product_scope", campaign["product"]),
        "niche": campaign.get("niche", "ngành hàng liên quan"),
        "target": Target(campaign).describe(),
        "budget_m": f"{campaign['budget_vnd'] / 1e6:,.0f}",
        "n_koc": campaign["n_koc"],
    }


def config_hash(obj) -> str:
    """Băm cấu hình để đặt run_id: cùng cấu hình -> cùng run -> chạy lại thì resume."""
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
