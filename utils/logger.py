# hari/utils/logger.py
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from functools import wraps

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_session_log_path = None

def init_session_log(session_id: str = None):
    global _session_log_path
    if session_id is None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    _session_log_path = LOG_DIR / f"session_{session_id}.json"
    with open(_session_log_path, "w") as f:
        json.dump([], f)
    return _session_log_path

def log_event(event: Dict[str, Any]):
    if _session_log_path is None:
        init_session_log()
    with open(_session_log_path, "r+") as f:
        data = json.load(f)
        data.append(event)
        f.seek(0)
        json.dump(data, f, indent=2)

def harilog(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        log_event({
            "timestamp": datetime.now().isoformat(),
            "function": func.__name__,
            "result_preview": str(result.get("dialogue", ""))[:100]
        })
        return result
    return wrapper
