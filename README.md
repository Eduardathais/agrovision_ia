# AgroVision AI

Sistema de monitoramento visual com detecção de objetos em tempo real (YOLOv8n) e agente de IA conversacional (Ollama + LLaMA 3). Exibe um dashboard com feed ao vivo da câmera, histórico de eventos, dados climáticos e alertas de previsão.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend / API | Python 3.11, FastAPI, Uvicorn |
| Detecção de objetos | OpenCV, Ultralytics YOLOv8n |
| Agente conversacional | Ollama (LLaMA 3) |
| Banco de dados | SQLite |
| Frontend | HTML5, CSS3, JavaScript, Jinja2 |
| Dados externos | Open-Meteo API (clima + alertas) |

## Pré-requisitos

- Python 3.10+
- [Ollama](https://ollama.com) instalado e rodando

## Instalação

```bash
pip install -r requirements.txt
cp .env.example .env
```

## Configuração

Edite o `.env` conforme necessário. Principais variáveis:

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `OLLAMA_MODEL` | `llama3` | Modelo Ollama |
| `CAMERA_SOURCE` | `0` | Webcam local, URL JPEG, RTSP ou HLS |
| `LATITUDE` | `-23.5` | Latitude para dados climáticos |
| `LONGITUDE` | `-46.6` | Longitude para dados climáticos |

**Exemplos de câmera:**
```bash
CAMERA_SOURCE=0                                              # webcam local
CAMERA_SOURCE=https://cameras.cetsp.com.br/Cams/200/4.jpg   # câmera CETSP SP
```

## Execução

```bash
# 1. Subir o Ollama (terminal separado)
ollama serve
ollama pull llama3   # só na primeira vez

# 2. Rodar o servidor
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Acesse: `http://localhost:8000`

## Rotas

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Dashboard principal |
| `GET` | `/video_feed` | Stream MJPEG da câmera |
| `GET` | `/events` | Eventos detectados (JSON) |
| `POST` | `/chat` | Chat com o agente |
| `POST` | `/chat/stream` | Chat com streaming (NDJSON) |
| `GET` | `/agro/dados` | Clima atual + alertas de previsão |
| `GET` | `/health` | Status do serviço |
