from asistente import procesar_mensaje
from models import Cita

EMAIL = "ana@correo.com"
TEL = "5512345678"


def test_reservar_en_varios_turnos(db):
    sesion = {}

    r = procesar_mensaje(db, sesion, "quiero una manicura", EMAIL, TEL)
    assert r["estado"] == "pregunta" and r["esperando"] == "fecha"

    r = procesar_mensaje(db, sesion, "mañana", EMAIL, TEL)
    assert r["estado"] == "pregunta" and r["esperando"] == "hora"

    r = procesar_mensaje(db, sesion, "a las 4", EMAIL, TEL)
    assert r["estado"] == "completo"
    assert db.query(Cita).count() == 1
    assert "dialogo" not in sesion


def test_reservar_en_un_solo_mensaje(db):
    r = procesar_mensaje(db, {}, "quiero un tinte mañana a las 10 am", EMAIL, TEL)
    assert r["estado"] == "completo"
    assert r["cita"]["servicio"] == "tinte"


def test_horario_ocupado_sugiere_alternativas(db):
    procesar_mensaje(db, {}, "quiero un tinte mañana a las 10 am", EMAIL, TEL)   # ocupa 10:00-11:30

    sesion = {}
    r = procesar_mensaje(db, sesion, "quiero una manicura mañana a las 10:30 am", EMAIL, TEL)
    assert r["estado"] == "pregunta" and "libre" in r["respuesta"]

    r = procesar_mensaje(db, sesion, "a las 12", EMAIL, TEL)
    assert r["estado"] == "completo"


def test_pide_el_contacto_cuando_falta_y_continua(db):
    sesion = {}
    r = procesar_mensaje(db, sesion, "quiero una manicura mañana a las 4", "", "")
    assert r["estado"] == "pregunta" and r["esperando"] == "contacto"

    r = procesar_mensaje(db, sesion, "listo", EMAIL, TEL)
    assert r["estado"] == "completo"


def test_servicio_desconocido_lista_las_opciones(db):
    r = procesar_mensaje(db, {}, "quiero una keratina mañana a las 4", EMAIL, TEL)
    assert r["estado"] == "pregunta" and r["esperando"] == "servicio"
    assert "manicura" in r["respuesta"]


def test_olvidalo_cancela_el_tramite(db):
    sesion = {}
    procesar_mensaje(db, sesion, "quiero una manicura", EMAIL, TEL)
    procesar_mensaje(db, sesion, "olvídalo", EMAIL, TEL)
    assert "dialogo" not in sesion


def test_cotizar_no_pierde_el_tramite_pendiente(db):
    sesion = {}
    procesar_mensaje(db, sesion, "quiero una manicura", EMAIL, TEL)
    r = procesar_mensaje(db, sesion, "¿cuánto cuesta un tinte?", EMAIL, TEL)
    assert "500" in r["respuesta"]
    assert "dialogo" in sesion