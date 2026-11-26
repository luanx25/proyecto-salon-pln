from asistente import procesar_mensaje
from models import Cita
from datetime import date, timedelta
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

def _reservar(db, texto="quiero una manicura mañana a las 4"):
    r = procesar_mensaje(db, {}, texto, EMAIL, TEL)
    assert r["estado"] == "completo"
    return r["cita"]["id"]


def test_cancelar_pide_confirmacion_y_cancela(db):
    cita_id = _reservar(db)
    sesion = {}

    r = procesar_mensaje(db, sesion, "cancela mi cita", EMAIL, TEL)
    assert r["estado"] == "pregunta" and r["esperando"] == "confirmar"
    assert db.get(Cita, cita_id).estado == "confirmada"        # todavía no se canceló

    r = procesar_mensaje(db, sesion, "sí", EMAIL, TEL)
    assert r["estado"] == "completo"
    assert db.get(Cita, cita_id).estado == "cancelada"


def test_decir_no_deja_la_cita_intacta(db):
    cita_id = _reservar(db)
    sesion = {}
    procesar_mensaje(db, sesion, "cancela mi cita", EMAIL, TEL)
    procesar_mensaje(db, sesion, "no", EMAIL, TEL)
    assert db.get(Cita, cita_id).estado == "confirmada"
    assert "dialogo" not in sesion


def test_cancelar_por_numero(db):
    cita_id = _reservar(db)
    sesion = {}
    r = procesar_mensaje(db, sesion, f"cancela la cita {cita_id}", EMAIL, TEL)
    assert r["esperando"] == "confirmar"
    procesar_mensaje(db, sesion, "sí", EMAIL, TEL)
    assert db.get(Cita, cita_id).estado == "cancelada"


def test_datos_ajenos_no_permiten_cancelar(db):
    cita_id = _reservar(db)
    r = procesar_mensaje(db, {}, "cancela mi cita", "otra@correo.com", "5598765432")
    assert "No encontré" in r["respuesta"]
    assert db.get(Cita, cita_id).estado == "confirmada"


def test_correo_correcto_con_telefono_equivocado_tampoco(db):
    _reservar(db)
    r = procesar_mensaje(db, {}, "cancela mi cita", EMAIL, "5598765432")
    assert "No encontré" in r["respuesta"]


def test_con_varias_citas_pide_el_numero(db):
    a = _reservar(db, "quiero una manicura mañana a las 4")
    b = _reservar(db, "quiero una manicura mañana a las 5")
    sesion = {}

    r = procesar_mensaje(db, sesion, "cancela mi cita", EMAIL, TEL)
    assert r["esperando"] == "cita"

    r = procesar_mensaje(db, sesion, str(b), EMAIL, TEL)
    assert r["esperando"] == "confirmar"

    procesar_mensaje(db, sesion, "sí", EMAIL, TEL)
    assert db.get(Cita, b).estado == "cancelada"
    assert db.get(Cita, a).estado == "confirmada"


def test_reprogramar_en_un_mensaje(db):
    cita_id = _reservar(db)
    r = procesar_mensaje(db, {}, "quiero cambiar mi cita para pasado mañana a las 5 pm", EMAIL, TEL)

    assert r["estado"] == "completo"
    nueva = db.get(Cita, cita_id).fecha_hora
    assert nueva.date() == date.today() + timedelta(days=2) and nueva.hour == 17


def test_reprogramar_pide_lo_que_falta(db):
    _reservar(db)
    sesion = {}

    r = procesar_mensaje(db, sesion, "quiero cambiar mi cita", EMAIL, TEL)
    assert r["esperando"] == "fecha"
    r = procesar_mensaje(db, sesion, "pasado mañana", EMAIL, TEL)
    assert r["esperando"] == "hora"
    r = procesar_mensaje(db, sesion, "a las 5", EMAIL, TEL)
    assert r["estado"] == "completo"


def test_consultar_citas(db):
    r = procesar_mensaje(db, {}, "¿cuáles son mis citas?", EMAIL, TEL)
    assert "No tienes citas" in r["respuesta"]

    _reservar(db)
    r = procesar_mensaje(db, {}, "¿cuáles son mis citas?", EMAIL, TEL)
    assert "manicura" in r["respuesta"]


def test_limite_de_citas_proximas(db):
    for hora in (10, 11, 12):
        _reservar(db, f"quiero una manicura mañana a las {hora}")

    r = procesar_mensaje(db, {}, "quiero una manicura mañana a las 1 pm", EMAIL, TEL)
    assert "Ya tienes" in r["respuesta"]