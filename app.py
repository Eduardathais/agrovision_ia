from __future__ import annotations
import os
import threading

import cv2
import numpy as np
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.config import SAVE_DIR
from services.capture_store import list_captures
from services.event_repository import init_db, list_events
from services.monitoring_agent import build_agent_messages, get_agent_status
from services.ollama_client import ask_ollama, get_ollama_status, stream_ollama, warmup_ollama
from services.schemas import ChatRequest, ChatResponse, Message
from services.scraping_service import get_agro_dados
from services.video_monitor import (
    generate_mjpeg_stream,
    get_camera_status,
    get_last_frame,
    process_stream,
)

app = FastAPI(title="AgroVision AI")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)

os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs(SAVE_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    threading.Thread(target=process_stream, daemon=True).start()
    threading.Thread(target=warmup_ollama, daemon=True).start()


# ── Página principal ──────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    events = list_events(20)
    captures = list_captures(12)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "events": events, "captures": captures},
    )


# ── Status e diagnóstico ──────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "AgroVision AI", "ollama": get_ollama_status()}


@app.get("/camera/status")
def camera_status():
    return get_camera_status()


@app.get("/agent/status")
def agent_status():
    return get_agent_status()


# ── Câmera ────────────────────────────────────────────────────────────────────

@app.get("/frame")
def get_frame():
    frame = get_last_frame()
    if frame is None:
        frame = np.full((480, 800, 3), 20, dtype=np.uint8)
    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        return JSONResponse(content={"message": "Erro ao converter frame."}, status_code=500)
    return Response(content=buffer.tobytes(), media_type="image/jpeg")


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ── Eventos ───────────────────────────────────────────────────────────────────

@app.get("/events")
def get_events():
    return JSONResponse(content=list_events(50))


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        messages = build_agent_messages(req.message, req.history)
        answer = ask_ollama(messages)
        new_history = req.history + [
            Message(role="user", content=req.message),
            Message(role="assistant", content=answer),
        ]
        return ChatResponse(answer=answer, history=new_history)
    except Exception as exc:
        print(f"[Chat] Erro interno: {exc}")
        return JSONResponse(status_code=500, content={"error": "Erro interno ao processar a mensagem."})


@app.get("/agro/dados")
def agro_dados():
    return JSONResponse(content=get_agro_dados())


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    messages = build_agent_messages(req.message, req.history)
    return StreamingResponse(
        stream_ollama(messages),
        media_type="application/x-ndjson",
    )
