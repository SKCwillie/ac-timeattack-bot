import json
from pathlib import Path

def normalize(s: str):
    """Lowercase, remove spaces, strip."""
    return s.lower().replace(" ", "").strip()

def lookup_real_name(steam_name: str, registry: dict):
    """
    Fuzzy match:
    - ignore case
    - ignore spaces
    - match if registry steam name appears anywhere in leaderboard steam name
    - match if leaderboard steam name appears anywhere in registry name
    """
    steam_norm = normalize(steam_name)

    for registered_steam, real in registry.items():
        reg_norm = normalize(registered_steam)

        if steam_norm == reg_norm:
            return real
        if reg_norm in steam_norm:
            return real
        if steam_norm in reg_norm:
            return real

    return None

def load_registry(path: Path):
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}
