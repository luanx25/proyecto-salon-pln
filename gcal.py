import logging
from functools import lru_cache
from pathlib import Path

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