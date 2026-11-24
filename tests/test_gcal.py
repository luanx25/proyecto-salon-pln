from datetime import datetime
from types import SimpleNamespace

from gcal import construir_evento


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