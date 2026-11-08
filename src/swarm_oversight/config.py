"""Paths, .env loading and model-role config. Never prints keys."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = ROOT / "sandbox" / "seed"
LOG_DIR = ROOT / "logs"
CACHE_DIR = ROOT / "cache"
RUNNER_IMAGE = "swarm-runner:0.1"

load_dotenv(ROOT / ".env")

PROVIDERS = {
    "deepseek": ("https://api.deepseek.com", "DEEPSEEK_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "google": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GOOGLE_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
}


def api_key(provider: str) -> str | None:
    return os.environ.get(PROVIDERS[provider][1]) or None


def models() -> dict:
    """Role -> {model: 'provider/model-id', ...extra params}."""
    return yaml.safe_load((ROOT / "configs" / "models.yaml").read_text())["roles"]
