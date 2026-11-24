from datetime import date, time

from dialogo import cargar, guardar, fusionar
from nlp import parse_mensaje, detectar_servicio, detectar_hora_suelta, normalizar

HOY = date(2026, 11, 23)


def pendiente(**extra):
    base = {"intencion": "reservar", "servicio": "manicura", "fecha": None,
            "hora": None, "cita_id": None, "esperando": "fecha"}
    return {**base, **extra}


def test_continua_el_tramite_con_lo_que_falta():
    estado = fusionar(pendiente(), parse_mensaje("mañana", hoy=HOY))
    assert estado["intencion"] == "reservar"
    assert estado["servicio"] == "manicura"          # se conserva
    assert estado["fecha"] == date(2026, 11, 24)     # se completa


def test_una_intencion_distinta_reinicia():
    estado = fusionar(pendiente(), parse_mensaje("cancela mi cita", hoy=HOY))
    assert estado["intencion"] == "cancelar"
    assert estado["servicio"] is None


def test_lo_nuevo_reemplaza_a_lo_anterior():
    estado = fusionar(pendiente(), parse_mensaje("mejor un tinte", hoy=HOY))
    assert estado["servicio"] == "tinte"


def test_hora_suelta_si_el_bot_la_pidio():
    estado = fusionar(pendiente(fecha=HOY, esperando="hora"), parse_mensaje("4", hoy=HOY))
    assert estado["hora"] == time(16, 0)


def test_guardar_y_cargar_conservan_los_datos():
    sesion = {}
    guardar(sesion, {**pendiente(fecha=HOY, hora=time(10, 30)), "esperando": "hora"})
    estado = cargar(sesion)
    assert estado["fecha"] == HOY and estado["hora"] == time(10, 30)


def test_el_dialogo_caduca():
    sesion = {}
    guardar(sesion, pendiente())
    sesion["dialogo"]["ts"] -= 16 * 60
    assert cargar(sesion) is None
    assert "dialogo" not in sesion


def test_reconoce_servicios_creados_desde_el_panel():
    assert detectar_servicio(normalizar("quiero keratina"), ["keratina"]) == "keratina"
    assert detectar_servicio(normalizar("quiero algunas cosas")) is None   # "unas" ya no coincide dentro de "algunas"


def test_hora_suelta():
    assert detectar_hora_suelta("4") == time(16, 0)
    assert detectar_hora_suelta("10:30") == time(10, 30)
    assert detectar_hora_suelta("4 de la tarde") == time(16, 0)
    assert detectar_hora_suelta("10 de diciembre") is None