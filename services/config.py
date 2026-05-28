from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()


def _parse_camera_source(raw: str) -> int | str:
    return int(raw) if raw.isdigit() else raw


OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_KEEP_ALIVE: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
AGENT_EVENT_LIMIT: int = int(os.getenv("AGENT_EVENT_LIMIT", "12"))
MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "8"))

CAMERA_SOURCE: int | str = _parse_camera_source(os.getenv("CAMERA_SOURCE", "0"))
CAMERA_RECONNECT_SECONDS: int = int(os.getenv("CAMERA_RECONNECT_SECONDS", "5"))

LATITUDE: float = float(os.getenv("LATITUDE", "-23.5"))
LONGITUDE: float = float(os.getenv("LONGITUDE", "-46.6"))
SCRAPING_CACHE_TTL_SECONDS: int = int(os.getenv("SCRAPING_CACHE_TTL_SECONDS", "3600"))

MODEL_PATH = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.45
SAVE_DIR = "static/captures"
DB_PATH = "detections.db"
MIN_CONSECUTIVE_FRAMES = 3
ALERT_COOLDOWN_SECONDS = 20
TARGET_CLASSES = {"person", "car", "motorcycle", "truck", "bus"}
