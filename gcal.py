import logging
from functools import lru_cache
from pathlib import Path
from datetime import timedelta
import google_auth_httplib2
import httplib2
from google.oauth2 import service_account
from googleapiclient.discovery import build

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


def registrar_cita(db, cita) -> bool:
    """Intenta crear el evento. Nunca rompe la reserva: si falla, la cita queda sin google_event_id."""
    if not gcal_habilitado():
        return False
    try:
        cita.google_event_id = crear_evento(cita)
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.exception("No se pudo crear el evento de Google Calendar")
        return False