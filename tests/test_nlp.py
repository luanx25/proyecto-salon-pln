from datetime import date, time

from nlp import detectar_fecha, detectar_hora, normalizar, detectar_cita_id, detectar_intencion
import pytest
HOY = date(2026, 11, 23)  # lunes


def fecha(texto):
    return detectar_fecha(normalizar(texto), hoy=HOY)


def hora(texto):
    return detectar_hora(normalizar(texto))


# ---------- fechas ----------

def test_manana_es_el_dia_siguiente():
    assert fecha("mañana") == date(2026, 11, 24)


def test_por_la_manana_no_es_manana():
    assert fecha("el viernes por la mañana") == date(2026, 11, 27)


def test_manana_por_la_manana():
    assert fecha("mañana por la mañana") == date(2026, 11, 24)


def test_pasado_manana_y_hoy():
    assert fecha("pasado mañana") == date(2026, 11, 25)
    assert fecha("hoy") == HOY
    assert fecha("esta tarde") == HOY


def test_en_n_dias_y_semanas():
    assert fecha("en 3 días") == date(2026, 11, 26)
    assert fecha("en una semana") == date(2026, 11, 30)


def test_dia_y_mes():
    assert fecha("el 5 de enero") == date(2027, 1, 5)          # ya pasó este año
    assert fecha("15 de diciembre") == date(2026, 12, 15)
    assert fecha("15 de diciembre de 2027") == date(2027, 12, 15)


def test_formato_numerico():
    assert fecha("15/12") == date(2026, 12, 15)
    assert fecha("el 28") == date(2026, 11, 28)
    assert fecha("el 10") == date(2026, 12, 10)                 # ya pasó este mes


def test_mismo_dia_de_la_semana_es_la_semana_siguiente():
    assert fecha("el lunes") == date(2026, 11, 30)


def test_fecha_imposible_o_ausente():
    assert fecha("31 de febrero") is None
    assert fecha("quiero una manicura") is None


# ---------- horas ----------

def test_9_15_pm_ya_no_se_confunde():          # bug original: devolvía 15:00
    assert hora("a las 9:15pm") == time(21, 15)


def test_10_20_am_ya_no_se_confunde():         # bug original: devolvía 20:00
    assert hora("a las 10:20 am") == time(10, 20)


def test_formatos_comunes():
    assert hora("15:00") == time(15, 0)
    assert hora("3:30pm") == time(15, 30)
    assert hora("11am") == time(11, 0)
    assert hora("12 pm") == time(12, 0)


def test_sin_meridiano_se_asume_horario_del_salon():
    assert hora("a las 4") == time(16, 0)
    assert hora("a las 10") == time(10, 0)
    assert hora("a las 12") == time(12, 0)


def test_franjas_del_dia():
    assert hora("a las 10 de la mañana") == time(10, 0)
    assert hora("a las 3 de la tarde") == time(15, 0)
    assert hora("a las 8 de la noche") == time(20, 0)


def test_horas_con_palabras():
    assert hora("a las tres y media") == time(15, 30)
    assert hora("a la una") == time(13, 0)
    assert hora("al mediodía") == time(12, 0)


def test_hora_invalida():
    assert hora("a las 27") is None

def intencion(texto):
    return detectar_intencion(normalizar(texto))


@pytest.mark.parametrize("texto, esperada", [
    ("Quiero una manicura mañana a las 4", "reservar"),
    ("quiero reservar mi cita para el viernes", "reservar"),
    ("Cancela mi cita", "cancelar"),
    ("ya no puedo ir", "cancelar"),
    ("quiero cambiar mi cita para el sábado", "reprogramar"),
    ("¿Cuándo es mi cita?", "consultar"),
    ("¿Cuánto cuesta un tinte?", "cotizar"),
    ("hola", "saludo"),
    ("buenas tardes quiero un peinado", "reservar"),
    ("sí", "afirmar"),
    ("no", "abortar"),
    ("olvídalo", "abortar"),
    ("blablabla", "ayuda"),
])
def test_intenciones(texto, esperada):
    assert intencion(texto) == esperada


def test_numero_de_cita():
    assert detectar_cita_id(normalizar("cancelar la cita 12")) == 12
    assert detectar_cita_id(normalizar("cita numero 15")) == 15
    assert detectar_cita_id(normalizar("quiero una cita 3 pm")) is None
    assert detectar_cita_id(normalizar("cita 12:30")) is None