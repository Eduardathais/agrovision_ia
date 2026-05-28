from __future__ import annotations
from collections import Counter
from dataclasses import dataclass

from services.config import AGENT_EVENT_LIMIT, MAX_HISTORY_MESSAGES
from services.event_repository import list_events
from services.schemas import Message
from services.scraping_service import get_agro_dados


@dataclass(frozen=True)
class AgentProfile:
    name: str
    role: str
    goal: str


AGENT_PROFILE = AgentProfile(
    name="Agente AgroVision",
    role="triagem operacional de eventos",
    goal="Analisar detecções recentes, explicar riscos e sugerir a próxima ação.",
)

_SYSTEM_PROMPT = (
    f"Você é o {AGENT_PROFILE.name}, um agente de {AGENT_PROFILE.role}. "
    f"Objetivo: {AGENT_PROFILE.goal} "
    "Trate os dados como monitoramento operacional autorizado de ambiente real. "
    "Responda em português do Brasil, de forma direta e útil. "
    "Use os eventos fornecidos como fonte principal. "
    "Não invente dados que não aparecem no contexto. "
    "Não tente identificar pessoas; fale apenas sobre eventos, riscos e próximas ações. "
    "Quando fizer sentido, organize a resposta em: leitura, risco e recomendação."
)


def build_event_context(events: list[dict]) -> str:
    if not events:
        return "Contexto operacional: nenhum evento registrado ainda."

    labels = [e["label"] for e in events]
    dist = Counter(labels)
    avg_conf = sum(e["confidence"] for e in events) / len(events)

    lines = [
        "Contexto operacional para o agente:",
        f"- Eventos considerados: {len(events)}",
        f"- Evento mais recente: {labels[0]} em {events[0]['event_time']}",
        f"- Distribuição: {', '.join(f'{k}: {v}' for k, v in dist.most_common())}",
        f"- Confiança média: {avg_conf:.2f}",
        "Eventos recentes:",
    ]
    for e in events:
        lines.append(f"  - #{e['id']} | {e['label']} ({e['confidence']:.2f}) em {e['event_time']}")

    return "\n".join(lines)


def normalize_history(history: list[Message]) -> list[dict]:
    filtered = [m for m in history if m.role in ("user", "assistant")]
    return [{"role": m.role, "content": m.content} for m in filtered[-MAX_HISTORY_MESSAGES:]]


def build_climate_context(dados: dict) -> str:
    clima = dados.get("clima", {})
    alertas_data = dados.get("alertas", {})

    if clima.get("erro"):
        return "Contexto climático: dados indisponíveis no momento."

    lines = ["Contexto climático atual (Open-Meteo):"]
    if clima.get("temperatura_c") is not None:
        lines.append(f"- Temperatura: {clima['temperatura_c']} °C")
    if clima.get("precipitacao_mm") is not None:
        lines.append(f"- Precipitação: {clima['precipitacao_mm']} mm")
    if clima.get("vento_kmh") is not None:
        lines.append(f"- Vento: {clima['vento_kmh']} km/h")
    if clima.get("umidade_pct") is not None:
        lines.append(f"- Umidade: {clima['umidade_pct']}%")

    alertas = alertas_data.get("alertas", [])
    if alertas:
        lines.append("Alertas climáticos (próximos 3 dias):")
        for a in alertas[:3]:
            lines.append(f"  - {a['tipo']} ({a['severidade']}) em {a['data']}: {a['valor']}")
    else:
        lines.append("Sem alertas climáticos para os próximos 3 dias.")

    return "\n".join(lines)


def build_agent_messages(question: str, history: list[Message]) -> list[dict]:
    events = list_events(AGENT_EVENT_LIMIT)
    dados = get_agro_dados()
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "system", "content": build_event_context(events)},
        {"role": "system", "content": build_climate_context(dados)},
        *normalize_history(history),
        {"role": "user", "content": question},
    ]


def get_agent_status() -> dict:
    events = list_events(AGENT_EVENT_LIMIT)
    context = build_event_context(events)
    return {
        "name": AGENT_PROFILE.name,
        "role": AGENT_PROFILE.role,
        "goal": AGENT_PROFILE.goal,
        "events_in_context": len(events),
        "context_preview": context[:600],
    }
