import re
import time as _reloj
from datetime import date, time

from nlp import detectar_hora_suelta

TTL_SEGUNDOS = 15 * 60          # el diálogo se olvida tras 15 min sin actividad
CAMPOS = ("servicio", "fecha", "hora", "cita_id")


def _serializar(estado: dict) -> dict:
    return {
        "intencion": estado["intencion"],
        "servicio": estado.get("servicio"),
        "fecha": estado["fecha"].isoformat() if estado.get("fecha") else None,
        "hora": estado["hora"].strftime("%H:%M") if estado.get("hora") else None,
        "cita_id": estado.get("cita_id"),
        "esperando": estado.get("esperando"),
        "ts": _reloj.time(),
    }


def _deserializar(crudo: dict) -> dict:
    return {
        "intencion": crudo["intencion"],
        "servicio": crudo.get("servicio"),
        "fecha": date.fromisoformat(crudo["fecha"]) if crudo.get("fecha") else None,
        "hora": time.fromisoformat(crudo["hora"]) if crudo.get("hora") else None,
        "cita_id": crudo.get("cita_id"),
        "esperando": crudo.get("esperando"),
    }


def cargar(sesion):
    crudo = sesion.get("dialogo")
    if not crudo:
        return None
    if _reloj.time() - crudo.get("ts", 0) > TTL_SEGUNDOS:
        sesion.pop("dialogo", None)
        return None
    try:
        return _deserializar(crudo)
    except (KeyError, ValueError, TypeError):
        sesion.pop("dialogo", None)
        return None


def guardar(sesion, estado: dict):
    sesion["dialogo"] = _serializar(estado)


def limpiar(sesion):
    sesion.pop("dialogo", None)


def fusionar(pendiente, analisis: dict) -> dict:
    """Combina lo que ya sabíamos con lo que dice el mensaje nuevo.

    - Un mensaje sin intención propia ("mañana", "a las 4", "sí") continúa el trámite pendiente.
    - Una intención distinta (ej. "cancela mi cita" en medio de una reserva) reinicia el trámite.
    - Lo nuevo reemplaza a lo anterior ("mejor un tinte").
    """
    intencion = analisis["intencion"]
    continua = bool(pendiente) and intencion in ("ayuda", "afirmar", pendiente["intencion"])
    base = pendiente if continua else {}

    estado = {"intencion": pendiente["intencion"] if continua else intencion}
    for campo in CAMPOS:
        nuevo = analisis.get(campo)
        estado[campo] = nuevo if nuevo is not None else base.get(campo)

    estado["esperando"] = base.get("esperando")     # lo último que el bot preguntó
    estado["afirmo"] = intencion == "afirmar"       # no se guarda: solo vale para este turno

    texto = analisis["texto_normalizado"]
    if estado["esperando"] == "hora" and estado["hora"] is None:
        estado["hora"] = detectar_hora_suelta(texto)
    if estado["esperando"] == "cita" and estado["cita_id"] is None and re.fullmatch(r"\d{1,6}", texto):
        estado["cita_id"] = int(texto)

    return estado