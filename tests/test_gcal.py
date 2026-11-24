from datetime import datetime
from types import SimpleNamespace

from gcal import construir_evento
from zoneinfo import ZoneInfo
from datetime import date

import gcal

def _cita():
    return SimpleNamespace(
        id=7,
        fecha_hora=datetime(2026, 12, 1, 10, 0),
        cliente_email="ana@correo.com",
        cliente_telefono="5512345678",
        mensaje_original="quiero un tinte",
        origen="landing",
        servicio=SimpleNamespace(nombre="tinte", duracion_min=90),
        empleado=SimpleNamespace(nombre="Michell"),
    )


def test_evento_dura_lo_que_el_servicio():
    ev = construir_evento(_cita())
    assert ev["start"]["dateTime"] == "2026-12-01T10:00:00"
    assert ev["end"]["dateTime"] == "2026-12-01T11:30:00"


def test_evento_lleva_marca_de_la_app_y_contacto():
    ev = construir_evento(_cita())
    assert ev["extendedProperties"]["private"]["cita_id"] == "7"
    assert "5512345678" in ev["description"]





class _FakeGoogle:
    def __init__(self, items):
        self.items = items

    def events(self):
        return self

    def list(self, **kwargs):
        return self

    def execute(self):
        return {"items": self.items}


def _evento(ini, fin, **extra):
    return {"start": {"dateTime": ini}, "end": {"dateTime": fin}, **extra}


def test_solo_cuentan_los_eventos_externos(monkeypatch):
    monkeypatch.setattr(gcal, "TZ", ZoneInfo("America/Mexico_City"))
    items = [
        _evento("2026-12-01T12:00:00-06:00", "2026-12-01T13:00:00-06:00"),                   # comida: bloquea
        _evento("2026-12-01T10:00:00-06:00", "2026-12-01T11:00:00-06:00",
                extendedProperties={"private": {"cita_id": "7"}}),                          # de la app: se ignora
        _evento("2026-12-01T15:00:00-06:00", "2026-12-01T16:00:00-06:00", transparency="transparent"),
        _evento("2026-12-01T17:00:00-06:00", "2026-12-01T18:00:00-06:00", status="cancelled"),
    ]
    monkeypatch.setattr(gcal, "_servicio", lambda: _FakeGoogle(items))

    bloqueos = gcal._bloqueos_google(date(2026, 12, 1))

    assert len(bloqueos) == 1
    assert bloqueos[0][0].hour == 12 and bloqueos[0][1].hour == 13


def test_evento_de_todo_el_dia_bloquea_el_dia(monkeypatch):
    items = [{"start": {"date": "2026-12-01"}, "end": {"date": "2026-12-02"}}]
    monkeypatch.setattr(gcal, "_servicio", lambda: _FakeGoogle(items))

    bloqueos = gcal._bloqueos_google(date(2026, 12, 1))

    assert bloqueos[0][0].hour == 0 and bloqueos[0][1].hour == 23