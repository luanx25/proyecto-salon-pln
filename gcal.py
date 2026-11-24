import logging
from functools import lru_cache
from pathlib import Path
from datetime import timedelta
import google_auth_httplib2
import httplib2
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time as _time
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_CALENDAR_ID, TIMEZONE

logger = logging.getLogger("gcal")

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def gcal_habilitado() -> bool:
    """True solo si hay ID de calendario y archivo de credenciales."""
    return bool(GOOGLE_CALENDAR_ID) and Path(GOOGLE_CREDENTIALS_FILE).is_file()


@lru_cache(maxsize=1)
def _credenciales():
    return service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )


def _servicio():
    """Cliente nuevo por llamada: httplib2 no es seguro entre hilos. Timeout de 10 s."""
    http = google_auth_httplib2.AuthorizedHttp(_credenciales(), http=httplib2.Http(timeout=10))
    return build("calendar", "v3", http=http, cache_discovery=False)

def _descripcion(cita) -> str:
    lineas = [
        f"Cliente: {cita.cliente_email}",
        f"Teléfono: {cita.cliente_telefono}",
        f"Servicio: {cita.servicio.nombre} ({cita.servicio.duracion_min} min)",
        f"Atiende: {cita.empleado.nombre}",
        f"Origen: {cita.origen}",
    ]
    if cita.mensaje_original:
        lineas.append(f"Mensaje original: {cita.mensaje_original}")
    lineas.append(f"Cita #{cita.id} (gestionada desde el sistema del salón)")
    return "\n".join(lineas)


def construir_evento(cita) -> dict:
    fin = cita.fecha_hora + timedelta(minutes=cita.servicio.duracion_min)
    return {
        "summary": f"{cita.servicio.nombre.capitalize()} · {cita.empleado.nombre}",
        "description": _descripcion(cita),
        "start": {"dateTime": cita.fecha_hora.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": fin.isoformat(), "timeZone": TIMEZONE},
        # Marca privada: así sabemos cuáles eventos creó la app (se usa en el commit 25)
        "extendedProperties": {"private": {"cita_id": str(cita.id), "origen": "salon-app"}},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 60}]},
    }


def crear_evento(cita) -> str:
    """Crea el evento en Google y devuelve su id. Lanza excepción si falla."""
    evento = _servicio().events().insert(calendarId=GOOGLE_CALENDAR_ID, body=construir_evento(cita)).execute()
    return evento["id"]




def _no_encontrado(error) -> bool:
    return isinstance(error, HttpError) and error.resp.status in (404, 410)


def actualizar_evento(cita) -> str:
    """Actualiza el evento. Si ya no existe en Google, lo vuelve a crear. Devuelve el id vigente."""
    try:
        _servicio().events().patch(
            calendarId=GOOGLE_CALENDAR_ID,
            eventId=cita.google_event_id,
            body=construir_evento(cita),
        ).execute()
        return cita.google_event_id
    except HttpError as e:
        if _no_encontrado(e):
            return crear_evento(cita)
        raise


def eliminar_evento(event_id: str) -> None:
    try:
        _servicio().events().delete(calendarId=GOOGLE_CALENDAR_ID, eventId=event_id).execute()
    except HttpError as e:
        if not _no_encontrado(e):   # si ya no existía, mejor: el resultado es el mismo
            raise


def sincronizar_cita(db, cita) -> str:
    """Deja el calendario igual que la cita. Devuelve 'ok', 'desactivado' o 'error'.

    Importante: quien la llame debe haber guardado (commit) sus cambios antes.
    """
    if not gcal_habilitado():
        return "desactivado"

    cita_id = cita.id
    try:
        if cita.estado == "cancelada":
            if cita.google_event_id:
                eliminar_evento(cita.google_event_id)
                cita.google_event_id = None
        elif cita.google_event_id:
            cita.google_event_id = actualizar_evento(cita)
        else:
            cita.google_event_id = crear_evento(cita)
        db.commit()
        return "ok"
    except Exception:
        db.rollback()
        logger.exception("No se pudo sincronizar la cita %s con Google Calendar", cita_id)
        return "error"

TZ = ZoneInfo(TIMEZONE)
CACHE_SEGUNDOS = 60
_CACHE: dict[date, tuple[float, list]] = {}


def _a_local(texto: str) -> datetime:
    """Convierte una fecha RFC3339 de Google a hora local sin zona (como guarda la BD)."""
    dt = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    return dt.astimezone(TZ).replace(tzinfo=None)


def _bloqueos_google(dia: date) -> list[tuple[datetime, datetime]]:
    inicio = datetime.combine(dia, time.min, tzinfo=TZ)
    fin = inicio + timedelta(days=1)

    respuesta = _servicio().events().list(
        calendarId=GOOGLE_CALENDAR_ID,
        timeMin=inicio.isoformat(),
        timeMax=fin.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=250,
    ).execute()

    bloqueos = []
    for ev in respuesta.get("items", []):
        if ev.get("status") == "cancelled":
            continue
        if ev.get("transparency") == "transparent":      # marcado como "disponible"
            continue
        if ev.get("extendedProperties", {}).get("private", {}).get("cita_id"):
            continue                                       # lo creó la app: la BD ya lo cuenta

        if "dateTime" in ev["start"]:
            bloqueos.append((_a_local(ev["start"]["dateTime"]), _a_local(ev["end"]["dateTime"])))
        else:                                              # evento de todo el día
            bloqueos.append((datetime.combine(dia, time.min), datetime.combine(dia, time.max)))

    return bloqueos


def bloqueos_del_dia(dia: date) -> list[tuple[datetime, datetime]]:
    if not gcal_habilitado():
        return []

    ahora = _time.monotonic()
    guardado = _CACHE.get(dia)
    if guardado and ahora - guardado[0] < CACHE_SEGUNDOS:
        return guardado[1]

    try:
        bloqueos = _bloqueos_google(dia)
    except Exception:
        # Si Google falla, la reserva sigue funcionando sin los bloqueos externos
        logger.warning("No se pudo leer Google Calendar; se ignoran los bloqueos externos.", exc_info=True)
        return []

    if len(_CACHE) > 200:
        _CACHE.clear()
    _CACHE[dia] = (ahora, bloqueos)
    return bloqueos


def hay_bloqueo_externo(inicio: datetime, fin: datetime) -> bool:
    return any(inicio < b_fin and fin > b_ini for b_ini, b_fin in bloqueos_del_dia(inicio.date()))