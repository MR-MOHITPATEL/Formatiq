import yaml
import os
from pathlib import Path


def load_config() -> dict:
    """
    Load config from environment variables (production) or config.yaml (local dev).
    Environment variables always take priority over config.yaml values.
    """
    # Start with defaults
    cfg: dict = {
        "youtube_api_key": "",
        "gemini_api_key": "",
        "gemini_model": "gemini-2.5-flash",
        "gemini_script_model": "gemini-2.5-pro",
        "anthropic_api_key": "",
        "groq_api_key": "",
        "groq_model": "compound-beta",
        "claude_model": "claude-sonnet-4-20250514",
        "niche": "Health / Nutrition / Wellness",
        "analysis_batch_size": 10,
        "max_retries": 3,
        "news_search_api_key": "",
        "competitor_channels": [],
        "direct_competitor_channels": [],
        "videos_per_format_point": 100,
        "script": {
            "niche": "doctor / pharmaceutical",
            "shorts_target_words": 150,
            "longform_target_words": 2000,
        },
    }

    # Load config.yaml if it exists (local development)
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r") as f:
            file_cfg = yaml.safe_load(f) or {}
        cfg.update(file_cfg)

    # Environment variables always override config.yaml (used in production)
    env_map = {
        "YOUTUBE_API_KEY":      "youtube_api_key",
        "GEMINI_API_KEY":       "gemini_api_key",
        "GEMINI_MODEL":         "gemini_model",
        "GEMINI_SCRIPT_MODEL":  "gemini_script_model",
        "ANTHROPIC_API_KEY":    "anthropic_api_key",
        "GROQ_API_KEY":         "groq_api_key",
        "GROQ_MODEL":           "groq_model",
        "CLAUDE_MODEL":         "claude_model",
        "NEWS_SEARCH_API_KEY":  "news_search_api_key",
    }
    for env_key, cfg_key in env_map.items():
        val = os.environ.get(env_key)
        if val:
            cfg[cfg_key] = val

    return cfg


config = load_config()
