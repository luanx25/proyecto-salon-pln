import logging
from functools import lru_cache
from pathlib import Path
from datetime import timedelta
import google_auth_httplib2
import httplib2
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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