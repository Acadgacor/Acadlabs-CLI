# src/acadlabs_cli/config.py
from pathlib import Path
from pydantic import BaseModel
import json

class Config(BaseModel):
    openrouter_api_key: str
    supabase_url: str
    supabase_key: str
    default_model: str = "anthropic/claude-3.5-sonnet"
    
    class Config:
        protected_namespaces = ()

CONFIG_DIR = Path.home() / ".acadlabs"
CONFIG_FILE = CONFIG_DIR / "config.json"

def load_config() -> Config:
    if not CONFIG_FILE.exists():
        raise ValueError("Config not found. Run 'acadlabs config init'")
    
    with open(CONFIG_FILE) as f:
        data = json.load(f)
    return Config(**data)

def save_config(config: Config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config.model_dump(), f, indent=2)