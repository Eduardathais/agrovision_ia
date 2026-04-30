from __future__ import annotations
import json
import threading
from typing import Generator

import requests

from services.config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_KEEP_ALIVE


def get_ollama_status() -> str:
    try:
        base_url = OLLAMA_URL.rsplit("/api/", 1)[0]
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        return "ok" if resp.ok else f"error:{resp.status_code}"
    except Exception as exc:
        return f"unreachable:{exc}"


def ask_ollama(messages: list[dict]) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=(10, OLLAMA_TIMEOUT))
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "")


def stream_ollama(messages: list[dict]) -> Generator[bytes, None, None]:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }
    try:
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=(10, OLLAMA_TIMEOUT)) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield json.dumps({"token": token}).encode() + b"\n"
                    if chunk.get("done"):
                        yield json.dumps({"done": True}).encode() + b"\n"
                        break
                except Exception:
                    continue
    except requests.exceptions.ReadTimeout:
        yield json.dumps({"error": "Ollama demorou demais para responder. Tente novamente."}).encode() + b"\n"
    except requests.exceptions.ConnectionError:
        yield json.dumps({"error": "Não foi possível conectar ao Ollama. Verifique se o serviço está rodando."}).encode() + b"\n"
    except Exception as exc:
        yield json.dumps({"error": str(exc)}).encode() + b"\n"


def warmup_ollama() -> None:
    try:
        ask_ollama([{"role": "user", "content": "Responda apenas: pronto"}])
        print(f"[Ollama] Modelo {OLLAMA_MODEL} aquecido.")
    except Exception as exc:
        print(f"[Ollama] Warmup falhou (normal se o Ollama ainda não está rodando): {exc}")
