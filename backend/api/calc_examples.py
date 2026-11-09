"""Ejemplos de cada estado para el OpenAPI de los endpoints de cálculo (HU-012).

Son de ejemplo y se rotulan así: `versions` dice `"ejemplo"` y las cifras son inventadas (R5). Salen de los ejemplos
de `specs/02-contratos.md`, corregidos con las decisiones 13 a 15. La web los usa como respuestas simuladas (HU-013).
Una prueba revisa que cada uno cumpla su modelo de `backend/api/calc_models.py`.
"""

from typing import Any

from backend.api.calc_models import ErrorBody

EXAMPLE_VERSIONS = {"dataset": "ejemplo", "rules": "ejemplo"}
EXAMPLE_NOTE = "Respuesta de ejemplo con cifras inventadas: el motor todavía no está construido."
WEIGHTS = {"water": 5, "frost": 3, "heat": 3, "soil": 3, "supply": 0, "market": 3}
DEFAULT_WEIGHTS = {"water": 4, "frost": 4, "heat": 3, "soil": 2, "supply": 2, "market": 2}


def _signal(status: str, level: str | None, score: int | None, reasons: list[str], indicators: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "status": status,
        "level": level,
        "critical": extra.pop("critical", False),
        "score": score,
        "counts": extra.pop("counts", True),
        "indicators": indicators,
        "reasons": reasons,
        **extra,
    }


def _light(light: str, action: str, basis: str, limiting: str | None, reasons: list[str], high_risk: bool = False) -> dict[str, Any]:
    return {
        "light": light,
        "action": action,
        "high_risk": high_risk,
        "weights_basis": basis,
        "limiting_signal": limiting,
        "reasons": reasons,
    }


SUITABLE = {
    "level": "suitable",
    # Dentro del óptimo de la papa en el catálogo (12 a 15 °C): 100.
    "score": 100,
    "basis": "municipality",
    "tmean_annual_c": 12.8,
    "altitude_m": 2660,
    "reasons": ["La temperatura media anual del municipio (12,8 °C, corregida a 2.660 m) está dentro del rango de la papa (8 a 16 °C)"],
}

SIGNALS_OK = {
    "water": _signal(
        "available",
        "favorable",
        86,
        ["En 7 de los últimos 10 años, la lluvia de agosto a diciembre cubrió lo que necesita la papa"],
        ["water_deficit_mm"],
        sources=[
            {"source_id": "imerg", "indicator": "precip_mm", "value": 410, "unit": "mm", "period": "2015-2024", "used": True},
            {"source_id": "nasa_power", "indicator": "precip_mm", "value": 380, "unit": "mm", "period": "2015-2024", "used": False},
            {"source_id": "nasa_power", "indicator": "soil_wetness_root", "value": 0.61, "unit": "fracción", "used": False},
        ],
    ),
    "frost": _signal(
        "available", "moderate", 58, ["Sembrando en agosto, heló en el llenado (diciembre) 12 de cada 100 años"], ["frost_freq_pct"]
    ),
    "heat": _signal(
        "available",
        "favorable",
        94,
        ["De agosto a diciembre, la máxima rara vez pasa de 22 °C; la papa aguanta hasta 30 °C"],
        ["tmax_p90_c"],
    ),
    "soil": _signal(
        "available",
        "favorable",
        80,
        ["pH estimado de 5,2 a 5,8, dentro del rango de la papa. Estimación de 250 m: confírmelo con un análisis de suelo"],
        ["ph"],
    ),
    "supply": _signal(
        "available",
        "unfavorable",
        30,
        ["En 2025 B (último dato, preliminar) se sembró 35 % más papa que en los tres semestres B anteriores"],
        ["planted_change_pct"],
        counts=False,
        sources=[
            {
                "source_id": "eva",
                "indicator": "planted_change_pct",
                "value": 35,
                "unit": "%",
                "period": "2025-B",
                "preliminary": True,
                "used": True,
            }
        ],
    ),
    "market": _signal("insufficient_data", None, None, ["Sin datos de mercado para la zona"], []),
}

DIAGNOSIS_OK = {
    "request": {"municipality_id": "15646", "crop_id": "papa", "sowing_date": "2027-08-02", "irrigated": False, "lot_id": None},
    "suitability": SUITABLE,
    "window": {
        "sowing_start": "2027-08-02",
        "harvest_estimate": "2027-12-27",
        "harvest_basis": "calendar",
        "supply_semester": {"year": 2025, "semester": "B", "preliminary": True},
    },
    "overall": _light(
        "green", "sow", "farmer", "frost", ["Con sus prioridades, la oferta no cuenta para la luz y ninguna otra señal es desfavorable"]
    ),
    "overall_default": _light(
        "yellow", "rotate", "default", "supply", ["Con el criterio de AgroSense, la oferta desfavorable pone la luz en amarillo"]
    ),
    "weights": WEIGHTS,
    "signals": SIGNALS_OK,
    "limitations": [EXAMPLE_NOTE, "Datos EVA del último año son preliminares", "Suelo estimado para el municipio, no para su lote"],
    "versions": EXAMPLE_VERSIONS,
}

DIAGNOSIS_NOT_SUITABLE = {
    "request": {"municipality_id": "25307", "crop_id": "papa", "sowing_date": "2027-08-02", "irrigated": False, "lot_id": None},
    "suitability": {
        "level": "not_suitable",
        "score": 0,
        "basis": "municipality",
        "tmean_annual_c": 28.4,
        "altitude_m": 289,
        "reasons": ["La temperatura media anual del municipio (28,4 °C) pasa de la que aguanta la papa (hasta 16 °C)"],
    },
    "window": None,
    "overall": _light("red", "rotate", "default", None, ["Este cultivo no se da en su zona: elija otro"]),
    "overall_default": _light("red", "rotate", "default", None, ["Este cultivo no se da en su zona: elija otro"]),
    "weights": DEFAULT_WEIGHTS,
    "signals": None,
    "limitations": [EXAMPLE_NOTE],
    "versions": EXAMPLE_VERSIONS,
}

# Sin lluvia para el municipio, la luz no se puede evaluar (regla 1 de la agregación). La cebolla de bulbo no tiene en su
# ficha qué etapas son sensibles a la helada: la señal es `insufficient_data`, nunca un riesgo (R1).
DIAGNOSIS_NOT_EVALUABLE = {
    **DIAGNOSIS_OK,
    "request": {**DIAGNOSIS_OK["request"], "crop_id": "cebolla_bulbo"},
    "suitability": {
        **SUITABLE,
        "score": 28,
        "reasons": [
            "La temperatura media anual del municipio (12,8 °C) está dentro del rango de la cebolla de bulbo (desde 10 °C), "
            "lejos de su óptimo (20 a 28 °C)"
        ],
    },
    "overall": _light(
        "not_evaluable", "review_data", "default", None, ["No hay datos de lluvia para esta zona: no se puede evaluar el agua"]
    ),
    "overall_default": _light(
        "not_evaluable", "review_data", "default", None, ["No hay datos de lluvia para esta zona: no se puede evaluar el agua"]
    ),
    "weights": DEFAULT_WEIGHTS,
    "signals": {
        **SIGNALS_OK,
        "water": _signal("insufficient_data", None, None, ["La fuente de lluvia de la región no tiene datos para este municipio"], []),
        "frost": _signal(
            "insufficient_data", None, None, ["La ficha de la cebolla de bulbo no dice qué etapas son sensibles a la helada"], []
        ),
    },
    "limitations": [EXAMPLE_NOTE, "Sin datos de lluvia para el municipio", "Sin datos de helada por etapa para este cultivo"],
}

# Una señal que no aplica: la ficha dice que ninguna etapa es sensible. Ningún cultivo del catálogo está así hoy, por
# eso el ejemplo usa un cultivo inventado y lo dice (R5).
DIAGNOSIS_NOT_APPLICABLE = {
    **DIAGNOSIS_OK,
    "request": {**DIAGNOSIS_OK["request"], "crop_id": "cultivo_de_ejemplo"},
    "suitability": {**SUITABLE, "reasons": ["Cultivo inventado para mostrar una señal que no aplica"]},
    "signals": {
        **SIGNALS_OK,
        "frost": _signal("not_applicable", None, None, ["Según su ficha, ninguna etapa de este cultivo es sensible a la helada"], []),
    },
    "limitations": [EXAMPLE_NOTE, "El cultivo de este ejemplo es inventado"],
}

_HEALTH = {
    "nitrogen": {
        "status": "available",
        "level": "favorable",
        "rule_ids": ["leguminosas"],
        "reasons": ["Dos de los tres ciclos tienen leguminosas (vicia y arveja), que fijan nitrógeno"],
    },
    "organic_carbon": {
        "status": "available",
        "level": "favorable",
        "rule_ids": ["materia_organica"],
        "reasons": ["El carbono orgánico estimado del suelo es bajo y la estrategia empieza con un abono verde"],
    },
    "soil_cover": {
        "status": "insufficient_data",
        "level": None,
        "rule_ids": [],
        "reasons": ["Aún no hay una regla con fuente que diga cuántos meses bastan"],
    },
    "pest_break": {
        "status": "available",
        "level": "favorable",
        "rule_ids": ["papa_espera"],
        "reasons": ["La papa vuelve al terreno después de dos ciclos de otras familias"],
    },
    "erosion": {
        "status": "available",
        "level": "moderate",
        "rule_ids": ["suelo_descubierto"],
        "reasons": ["Con pendiente de 9 %, el suelo queda descubierto 2 meses"],
    },
}


def _cycle(n: int, crop: str, sow: str, harvest: str, light: str | None, limiting: str | None) -> dict[str, Any]:
    return {
        "cycle": n,
        "crop_id": crop,
        "sowing_date": sow,
        "harvest_estimate": harvest,
        "harvest_basis": "calendar",
        "light": light,
        "light_default": light,
        "limiting_signal": limiting,
        "high_risk": False,
        "diagnosis": None,
    }


ROTATIONS = {
    "strategies": [
        {
            "rank": 1,
            "kind": "suggested",
            "crop_ids": ["avena_vicia", "arveja", "papa"],
            "total_score": 76,
            "scores": {"water": 74, "soil": 88, "income": 60, "risk": 71},
            "vs_current": {"water": 6, "soil": 38, "income": -9, "risk": 12, "total": 15},
            "cycles": [
                _cycle(1, "avena_vicia", "2027-01-04", "2027-04-19", "green", "water"),
                _cycle(2, "arveja", "2027-04-26", "2027-08-23", "yellow", "frost"),
                _cycle(3, "papa", "2027-08-30", "2028-01-24", "green", "frost"),
            ],
            "soil_health": _HEALTH,
            "reasons": [
                "Empieza con un abono verde y su suelo tiene poco carbono orgánico",
                "Gana 15 puntos frente a lo que siembra hoy, sobre todo en suelo",
            ],
            "limitations": ["Suelo estimado para el municipio, no para su lote"],
        }
    ],
    "current_strategy": {
        "rank": None,
        "kind": "current",
        "crop_ids": ["papa", "arveja", "papa"],
        "total_score": 61,
        "scores": {"water": 68, "soil": 50, "income": 69, "risk": 59},
        "cycles": [
            _cycle(1, "papa", "2027-01-04", "2027-05-31", "yellow", "frost"),
            _cycle(2, "arveja", "2027-06-07", "2027-10-04", "green", "water"),
            _cycle(3, "papa", "2027-10-11", "2028-03-06", "yellow", "water"),
        ],
        "soil_health": {
            **_HEALTH,
            "pest_break": {
                "status": "available",
                "level": "unfavorable",
                "rule_ids": ["papa_espera"],
                "reasons": ["La papa vuelve después de un solo ciclo de otra familia"],
            },
        },
        "issues": [
            {
                "cycle": 3,
                "kind": "rule",
                "rule_id": "papa_espera",
                "reason": "La papa vuelve al terreno después de un solo ciclo de otra familia",
            }
        ],
        "reasons": ["Es la rotación que usted viene haciendo: las demás se comparan contra ella"],
        "limitations": [],
    },
    "excluded": [
        {
            "crop_ids": ["papa", "arveja", "haba"],
            "cycle": 1,
            "kind": "rule",
            "rule_id": "familia_seguida",
            "reason": "Repite la familia de la papa, que había antes en el terreno",
        },
        {
            "crop_ids": ["arveja", "papa", "maiz"],
            "cycle": 2,
            "kind": "high_risk",
            "signal": "frost",
            "reason": "Alto riesgo en el ciclo 2: heladas frecuentes en el llenado de la papa",
        },
    ],
    "excluded_counts": {"rule": 212, "high_risk": 48, "not_suitable": 30, "soil_ph": 0},
    "weights": {"water": 3, "soil": 5, "income": 2, "risk": 4},
    "soil_basis": "municipality",
    "slope_basis": "municipality",
    "limitations": [EXAMPLE_NOTE, "Compara estrategias según reglas con fuente. No predice cuánto va a mejorar el suelo"],
    "versions": EXAMPLE_VERSIONS,
}

WATER_PLAN = {
    "request": {
        "municipality_id": "15646",
        "total_area_ha": 1.26,
        "crops": [{"crop_id": "papa", "area_pct": 100, "sowing_date": "2027-08-02"}],
    },
    "crops": [
        {
            "crop_id": "papa",
            "area_ha": 1.26,
            "sowing_date": "2027-08-02",
            "harvest_estimate": "2027-12-27",
            "harvest_basis": "calendar",
            "months": [
                {
                    "year": 2027,
                    "month": 9,
                    "status": "available",
                    "stage": "development",
                    "need_mm": 95,
                    "rain_mm": {"normal": 70, "dry": 41},
                    "deficit_mm": {"normal": [20, 30], "dry": [48, 62]},
                    "volume_m3": {"normal": [252, 378], "dry": [605, 781]},
                },
                {
                    "year": 2027,
                    "month": 10,
                    "status": "insufficient_data",
                    "stage": "mid",
                    "need_mm": 120,
                    "rain_mm": {"normal": None, "dry": None},
                    "deficit_mm": {"normal": None, "dry": None},
                    "volume_m3": {"normal": None, "dry": None},
                },
            ],
            "total_volume_m3": {"normal": [900, 1300], "dry": [2100, 2700]},
        }
    ],
    "farm": {
        "months": [{"year": 2027, "month": 9, "volume_m3": {"normal": [252, 378], "dry": [605, 781]}}],
        "total_volume_m3": {"normal": [900, 1300], "dry": [2100, 2700]},
    },
    "soil_moisture": [{"month": 9, "source_id": "nasa_power", "indicator": "soil_wetness_root", "value": 0.61, "unit": "fracción"}],
    "sources": {"rain": "imerg", "et0": "nasa_power", "soil": "soilgrids"},
    "soil_basis": "municipality",
    "limitations": [EXAMPLE_NOTE, "Es una estimación con el clima de la zona: verifique la humedad del suelo en su lote"],
    "versions": EXAMPLE_VERSIONS,
}

CHANGES = {
    "request": {"municipality_id": "15646", "crop_id": "papa", "irrigated": False},
    "periods": {
        "before": {"period_id": "p1981_2000", "start_year": 1981, "end_year": 2000, "source_id": "nasa_power"},
        "after": {"period_id": "p2005_2024", "start_year": 2005, "end_year": 2024, "source_id": "nasa_power"},
    },
    "suitability": {
        **SUITABLE,
        "reasons": ["La temperatura media anual del municipio (12,8 °C) está dentro del rango de la papa (8 a 16 °C)"],
    },
    "months": [
        {
            "month": 1,
            "frost_freq_pct": {"status": "available", "before": 30, "after": 18, "change": -12},
            "precip_normal_mm": {"status": "available", "before": 28, "after": 35, "change": 7},
            "tmax_p90_c": {"status": "insufficient_data", "before": None, "after": 21.4, "change": None},
        }
    ],
    "best_windows": {
        "before": [{"month": 3, "limiting_signal": "frost", "limiting_score": 64, "high_risk": False}],
        "after": [{"month": 4, "limiting_signal": "water", "limiting_score": 68, "high_risk": False}],
    },
    "weights_basis": "default",
    "reasons": ["Entre 1981 y 2000 heló en enero en 30 de cada 100 años; entre 2005 y 2024, en 18"],
    "limitations": [
        EXAMPLE_NOTE,
        "NASA POWER es un reanálisis, no una observación directa",
        "La oferta, el mercado y el suelo son los mismos en los dos periodos",
    ],
    "versions": EXAMPLE_VERSIONS,
}

TRENDS = {
    "request": {"municipality_id": "15646", "crop_id": "papa", "sowing_date": "2027-08-02"},
    "water": {"status": "available", "source_id": "imerg", "unit": "mm", "points": [{"year": 2015, "precip_mm": 410, "need_mm": 465}]},
    "supply": {"status": "insufficient_data", "source_id": "eva", "unit": "ha", "semester": "B", "points": []},
    "ndvi": {"status": "available", "source_id": "modis_ndvi", "quality": "ok", "points": [{"period": 1, "ndvi_normal": 0.52}]},
    "versions": EXAMPLE_VERSIONS,
}

SOIL = {
    "municipality_id": "15646",
    "ph": {"value": 5.5, "p05": 5.1, "p95": 5.9},
    "soc_g_kg": {"value": 31.0, "p05": 22.0, "p95": 42.0},
    "nitrogen_g_kg": 2.4,
    "clay_pct": 28.0,
    "sand_pct": 40.0,
    "silt_pct": 32.0,
    "texture_class": "franco arcilloso",
    "slope_pct": 9.0,
    "cells": 9,
    "quality": "ok",
    "source_id": "soilgrids",
    "versions": EXAMPLE_VERSIONS,
}


def error(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "request_id": "00000000-0000-4000-8000-000000000000"}}


ERRORS = {
    401: error("unauthorized", "Inicie sesión para continuar."),
    404: error("not_found", "Ese lote no existe o no es suyo."),
    422: error("invalid_input", "Hay datos que no son válidos. Revise: priorities."),
    501: error("not_implemented", "Este cálculo todavía no está disponible."),
    503: error("dataset_unavailable", "Los datos de AgroSense no están disponibles en este momento. Intente de nuevo más tarde."),
}

SUMMARIES = {
    401: "Sin sesión, o con `lot_id` y sin sesión",
    404: "Un lote o una temporada que no existe o es de otro usuario",
    422: "Entrada inválida",
    501: "El motor todavía no está construido",
    503: "El dataset publicado no está",
}


def responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """Las respuestas de error de una ruta en el OpenAPI (HU-012): la forma única de los errores, con su ejemplo."""
    return {
        code: {
            "model": ErrorBody,
            "content": {"application/json": {"examples": {"error": {"summary": SUMMARIES[code], "value": ERRORS[code]}}}},
        }
        for code in codes
    }
