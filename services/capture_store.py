from __future__ import annotations
import os
from services.config import SAVE_DIR


def list_captures(limit: int = 12) -> list[str]:
    if not os.path.isdir(SAVE_DIR):
        return []
    files = sorted(
        (f for f in os.listdir(SAVE_DIR) if f.lower().endswith(".jpg")),
        reverse=True,
    )
    return [f"/static/captures/{f}" for f in files[:limit]]
