import logging
from typing import Any

def safe_json_loads(s: str, fallback: Any = None):
    """Safely parse JSON, return fallback on error."""
    import json
    try:
        return json.loads(s)
    except Exception as e:
        logging.warning(f"JSON parse error: {e}")
        return fallback

# Add more shared utilities as needed
