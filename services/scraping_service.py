"""
Camada de integração externa: coleta dados públicos para enriquecer
o contexto operacional do AgroVision AI.

Fontes:
  - Open-Meteo API  (clima atual)
  - Open-Meteo API  (previsão 3 dias com geração de alertas de risco)

Boas práticas:
  - Cache em memória com TTL (evita sobrecarga nas fontes)
  - Fallback para cache antigo em caso de falha
  - Tratamento de erro gracioso — nunca propaga exceção para a rota
  - Dados retornados em formato estruturado (dict/JSON)
"""
from __future__ import annotations

import time
from typing import Optional

import requests

from services.config import LATITUDE, LONGITUDE, SCRAPING_CACHE_TTL_SECONDS

# ── Mapeamento de códigos WMO → alertas de risco ─────────────────────────────
# Fonte: https://open-meteo.com/en/docs — WMO Weather interpretation codes
_WMO_ALERTAS: dict[int, tuple[str, str]] = {
    # (tipo, severidade)
    65: ("Chuva intensa", "Severo"),
    67: ("Chuva congelante intensa", "Extremo"),
    75: ("Neve intensa", "Severo"),
    82: ("Pancadas de chuva fortes", "Severo"),
    86: ("Neve forte", "Severo"),
    95: ("Trovoada", "Severo"),
    96: ("Trovoada com granizo", "Extremo"),
    99: ("Trovoada intensa com granizo", "Extremo"),
}
_VENTO_ALERTAS = [(90, "Extremo"), (70, "Severo"), (50, "Moderado")]
_PRECIP_ALERTAS = [(50, "Extremo"), (30, "Severo"), (15, "Moderado")]

# ── Cache em memória ─────────────────────────────────────────────────────────

_weather_cache: Optional[dict] = None
_weather_cache_ts: float = 0.0

_forecast_cache: Optional[dict] = None
_forecast_cache_ts: float = 0.0


# ── Clima atual (Open-Meteo) ─────────────────────────────────────────────────

def get_weather() -> dict:
    """Retorna condições climáticas atuais para as coordenadas configuradas."""
    global _weather_cache, _weather_cache_ts

    now = time.time()
    if _weather_cache and (now - _weather_cache_ts) < SCRAPING_CACHE_TTL_SECONDS:
        return {**_weather_cache, "cached": True}

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
                "current": [
                    "temperature_2m",
                    "precipitation",
                    "wind_speed_10m",
                    "relative_humidity_2m",
                    "weather_code",
                ],
                "timezone": "America/Sao_Paulo",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("current", {})

        result = {
            "temperatura_c": data.get("temperature_2m"),
            "precipitacao_mm": data.get("precipitation"),
            "vento_kmh": data.get("wind_speed_10m"),
            "umidade_pct": data.get("relative_humidity_2m"),
            "codigo_tempo": data.get("weather_code"),
            "fonte": "Open-Meteo",
            "cached": False,
            "erro": None,
        }
        _weather_cache = result
        _weather_cache_ts = now
        return result

    except requests.exceptions.ConnectionError:
        return _weather_fallback("Não foi possível conectar ao Open-Meteo.")
    except requests.exceptions.Timeout:
        return _weather_fallback("Open-Meteo não respondeu a tempo.")
    except Exception as exc:
        return _weather_fallback(f"Erro inesperado: {type(exc).__name__}")


def _weather_fallback(msg: str) -> dict:
    if _weather_cache:
        return {**_weather_cache, "cached": True, "aviso": msg}
    return {
        "temperatura_c": None, "precipitacao_mm": None, "vento_kmh": None,
        "umidade_pct": None, "codigo_tempo": None,
        "fonte": "Open-Meteo", "cached": False, "erro": msg,
    }


# ── Alertas de risco (previsão 3 dias via Open-Meteo) ───────────────────────

def get_alertas_previsao() -> dict:
    """
    Gera alertas de risco climático para os próximos 3 dias com base na
    previsão Open-Meteo. Alertas gerados por thresholds de vento,
    precipitação e códigos WMO mapeados para severidade.
    """
    global _forecast_cache, _forecast_cache_ts

    now = time.time()
    if _forecast_cache and (now - _forecast_cache_ts) < SCRAPING_CACHE_TTL_SECONDS:
        return {**_forecast_cache, "cached": True}

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
                "daily": [
                    "weather_code",
                    "precipitation_sum",
                    "wind_speed_10m_max",
                    "temperature_2m_max",
                    "temperature_2m_min",
                ],
                "timezone": "America/Sao_Paulo",
                "forecast_days": 3,
            },
            timeout=10,
        )
        resp.raise_for_status()
        daily = resp.json().get("daily", {})

        datas = daily.get("time", [])
        codigos = daily.get("weather_code", [])
        precipitacoes = daily.get("precipitation_sum", [])
        ventos = daily.get("wind_speed_10m_max", [])

        alertas = []
        for i, data in enumerate(datas):
            codigo = codigos[i] if i < len(codigos) else 0
            precip = precipitacoes[i] if i < len(precipitacoes) else 0.0
            vento = ventos[i] if i < len(ventos) else 0.0

            # Alerta por código WMO
            if codigo in _WMO_ALERTAS:
                tipo, sev = _WMO_ALERTAS[codigo]
                alertas.append({"tipo": tipo, "severidade": sev, "data": data,
                                 "valor": f"código WMO {codigo}"})

            # Alerta por vento
            for limiar, sev in _VENTO_ALERTAS:
                if vento >= limiar:
                    alertas.append({"tipo": "Vento forte", "severidade": sev,
                                    "data": data, "valor": f"{vento:.0f} km/h"})
                    break

            # Alerta por precipitação
            for limiar, sev in _PRECIP_ALERTAS:
                if precip >= limiar:
                    alertas.append({"tipo": "Chuva acumulada", "severidade": sev,
                                    "data": data, "valor": f"{precip:.1f} mm"})
                    break

        result = {
            "alertas": alertas,
            "total": len(alertas),
            "previsao_dias": 3,
            "fonte": "Open-Meteo (previsão)",
            "cached": False,
            "erro": None,
        }
        _forecast_cache = result
        _forecast_cache_ts = now
        return result

    except Exception as exc:
        fallback = {"alertas": [], "total": 0, "previsao_dias": 3,
                    "fonte": "Open-Meteo (previsão)", "cached": False,
                    "erro": f"{type(exc).__name__}: previsão indisponível"}
        if _forecast_cache:
            return {**_forecast_cache, "cached": True, "aviso": fallback["erro"]}
        return fallback


# ── Ponto de entrada unificado ───────────────────────────────────────────────

def get_agro_dados() -> dict:
    """Retorna clima atual + alertas de previsão em um único dict."""
    return {
        "clima": get_weather(),
        "alertas": get_alertas_previsao(),
    }
