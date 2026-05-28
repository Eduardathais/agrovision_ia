from __future__ import annotations
import os
import time
import uuid
import threading
from collections import defaultdict
from datetime import datetime

import cv2
import numpy as np
import requests
from ultralytics import YOLO

from services.config import (
    CAMERA_SOURCE,
    CAMERA_RECONNECT_SECONDS,
    MODEL_PATH,
    CONFIDENCE_THRESHOLD,
    SAVE_DIR,
    MIN_CONSECUTIVE_FRAMES,
    ALERT_COOLDOWN_SECONDS,
    TARGET_CLASSES,
)
from services.event_repository import save_event

_last_frame: np.ndarray | None = None
_last_frame_lock = threading.Lock()
_camera_online = False
_camera_connected = False

# Limitação: _detection_state e _last_alert_time são indexados apenas por label.
# Dois objetos da mesma classe no frame (ex: dois carros) compartilham o mesmo
# contador e cooldown — o segundo objeto fica suprimido durante o período de
# cooldown do primeiro. Para corrigir, usar chave (label, região_bbox) ou
# o rastreador ByteTrack do Ultralytics (model.track()).
_detection_state: dict[str, int] = defaultdict(int)
_last_alert_time: dict[str, float] = defaultdict(float)
_model: YOLO | None = None


def _get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
    return _model


def _is_snapshot_url(source: int | str) -> bool:
    """True se source for uma URL de snapshot JPEG/PNG (ex: câmeras CETSP)."""
    if not isinstance(source, str):
        return False
    return source.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png"))


def _fetch_snapshot(url: str) -> tuple[bool, np.ndarray | None]:
    """Busca um frame de câmera snapshot HTTP (tipo CETSP)."""
    try:
        resp = requests.get(url, timeout=5, headers={"User-Agent": "AgroVision-AI/1.0"})
        resp.raise_for_status()
        arr = np.frombuffer(resp.content, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return (frame is not None), frame
    except Exception:
        return False, None


def get_last_frame() -> np.ndarray | None:
    with _last_frame_lock:
        return _last_frame.copy() if _last_frame is not None else None


def get_camera_status() -> dict:
    with _last_frame_lock:
        has_frame = _last_frame is not None
    source = CAMERA_SOURCE
    if isinstance(source, int):
        source_type = "webcam"
    elif _is_snapshot_url(source):
        source_type = "snapshot"
    else:
        source_type = "stream"
    return {
        "online": _camera_online,
        "connected": _camera_connected,
        "has_live_frame": has_frame,
        "source_type": source_type,
    }


def _make_status_frame(message: str) -> np.ndarray:
    frame = np.full((480, 800, 3), 20, dtype=np.uint8)
    cv2.putText(frame, "AgroVision AI", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 3)
    cv2.putText(frame, message, (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 160, 220), 2)
    return frame


def _draw_box(frame: np.ndarray, x1: int, y1: int, x2: int, y2: int, label: str, conf: float) -> None:
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(
        frame, f"{label} {conf:.2f}",
        (x1, max(20, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2,
    )


def _should_alert(label: str) -> bool:
    return (time.time() - _last_alert_time[label]) > ALERT_COOLDOWN_SECONDS


def _process_frame(frame: np.ndarray, model: YOLO) -> np.ndarray:
    """Executa YOLO no frame, salva eventos e retorna o frame anotado."""
    results = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)

    found_labels: set[str] = set()
    best_conf: dict[str, float] = {}

    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            label = model.names[cls_id]
            if label not in TARGET_CLASSES:
                continue
            found_labels.add(label)
            if label not in best_conf or conf > best_conf[label]:
                best_conf[label] = conf
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            _draw_box(frame, x1, y1, x2, y2, label, conf)

    for label in TARGET_CLASSES:
        _detection_state[label] = _detection_state[label] + 1 if label in found_labels else 0

    alerting_labels = [
        label for label in found_labels
        if _detection_state[label] >= MIN_CONSECUTIVE_FRAMES and _should_alert(label)
    ]

    if alerting_labels:
        frame_id = str(uuid.uuid4())[:8]
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{frame_id}.jpg"
        filepath = os.path.join(SAVE_DIR, filename)
        cv2.imwrite(filepath, frame)
        image_url = f"/static/captures/{filename}"

        for label in alerting_labels:
            event_id = str(uuid.uuid4())[:8]
            save_event(event_id, label, best_conf.get(label, 0.0), image_url)
            _last_alert_time[label] = time.time()
            print(f"[VideoMonitor] Evento: {label} conf={best_conf.get(label, 0):.2f} -> {filepath}")

    return frame


def process_stream() -> None:
    global _camera_online
    _camera_online = True
    model = _get_model()

    if _is_snapshot_url(CAMERA_SOURCE):
        _process_snapshot_loop(model)
    else:
        _process_capture_loop(model)


def _process_snapshot_loop(model: YOLO) -> None:
    """Loop para câmeras que servem snapshots JPEG via HTTP (ex: CETSP)."""
    global _last_frame, _camera_connected

    print(f"[VideoMonitor] Modo snapshot JPEG: {CAMERA_SOURCE}")
    consecutive_failures = 0

    while True:
        ok, frame = _fetch_snapshot(CAMERA_SOURCE)

        if not ok:
            consecutive_failures += 1
            _camera_connected = False
            if consecutive_failures == 1:
                print(f"[VideoMonitor] Falha ao buscar snapshot. Tentando em {CAMERA_RECONNECT_SECONDS}s...")
            with _last_frame_lock:
                _last_frame = _make_status_frame("Aguardando câmera...")
            time.sleep(CAMERA_RECONNECT_SECONDS)
            continue

        if consecutive_failures > 0:
            print(f"[VideoMonitor] Snapshot restaurado: {CAMERA_SOURCE}")
        consecutive_failures = 0
        _camera_connected = True

        frame = _process_frame(frame, model)
        with _last_frame_lock:
            _last_frame = frame.copy()

        time.sleep(0.5)


def _process_capture_loop(model: YOLO) -> None:
    """Loop para webcam local ou streams RTSP/HLS/MJPEG via cv2.VideoCapture."""
    global _last_frame, _camera_connected

    while True:
        cap = cv2.VideoCapture(CAMERA_SOURCE)
        _camera_connected = cap.isOpened()

        if not cap.isOpened():
            print(f"[VideoMonitor] Falha ao abrir: {CAMERA_SOURCE}. Tentando em {CAMERA_RECONNECT_SECONDS}s...")
            with _last_frame_lock:
                _last_frame = _make_status_frame("Aguardando câmera...")
            time.sleep(CAMERA_RECONNECT_SECONDS)
            continue

        print(f"[VideoMonitor] Câmera conectada: {CAMERA_SOURCE}")

        while True:
            ok, frame = cap.read()
            if not ok:
                print("[VideoMonitor] Stream interrompido. Reconectando...")
                _camera_connected = False
                break

            frame = _process_frame(frame, model)
            with _last_frame_lock:
                _last_frame = frame.copy()

            time.sleep(0.05)

        cap.release()
        time.sleep(CAMERA_RECONNECT_SECONDS)


def generate_mjpeg_stream():
    while True:
        with _last_frame_lock:
            frame = _last_frame.copy() if _last_frame is not None else None

        if frame is None:
            frame = _make_status_frame("Aguardando câmera...")

        success, buffer = cv2.imencode(".jpg", frame)
        if success:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )
        time.sleep(0.04)
