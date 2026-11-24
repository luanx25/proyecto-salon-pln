import re
import unicodedata
from datetime import date, time, timedelta


SINONIMOS_SERVICIOS = {
    "manicura": "manicura",
    "manicure": "manicura",
    "arreglo de manos": "manicura",
    "unas": "manicura",

    "pedicura": "pedicura",
    "pedicure": "pedicura",
    "arreglo de pies": "pedicura",

    "corte": "corte de cabello",
    "corte de cabello": "corte de cabello",
    "cortarme el cabello": "corte de cabello",
    "cortar el cabello": "corte de cabello",
    "cortarme el pelo": "corte de cabello",

    "tinte": "tinte",
    "color": "tinte",
    "coloracion": "tinte",
    "pintarme": "tinte",
    "pintar el cabello": "tinte",

    "peinado": "peinado",
    "peinarme": "peinado",
}
# Primera hora de atención. Debe coincidir con HORA_APERTURA de services.py
HORA_MAS_TEMPRANA = 9

NUMEROS = {
    "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
}
_NUM_RE = "|".join(NUMEROS)

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
_MESES_RE = "|".join(MESES)

DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3,
    "viernes": 4, "sabado": 5, "domingo": 6,
}

# "por la mañana", "en la mañana"... son franjas del día, no "el día de mañana"
FRANJA_MANANA_RE = re.compile(r"\b(?:por|en|de|a)\s+la\s+manana\b")


def normalizar(texto: str) -> str:
    texto = texto.lower()

    # Quita acentos y convierte ñ en n para simplificar el procesamiento.
    texto = "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )

    # Deja letras, números, espacios y dos puntos.
    texto = re.sub(r"[^a-z0-9\s:/]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def detectar_intencion(texto: str) -> str:
    if re.search(r"cancelar|anular", texto):
        return "cancelar"

    if re.search(r"cuanto|cuesta|precio|cotiz", texto):
        return "cotizar"

    if re.search(r"reservar|agendar|apartar|cita|quiero", texto):
        return "reservar"

    return "consultar"


def detectar_servicio(texto: str):
    # Se ordenan de mayor a menor longitud para detectar frases más específicas primero.
    sinonimos_ordenados = sorted(
        SINONIMOS_SERVICIOS.items(),
        key=lambda item: len(item[0]),
        reverse=True
    )

    for frase, servicio_canonico in sinonimos_ordenados:
        if frase in texto:
            return servicio_canonico

    return None
def _a_numero(token: str) -> int:
    return int(token) if token.isdigit() else NUMEROS[token]


def _fecha_valida(anio: int, mes: int, dia: int):
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def _sin_anio(hoy: date, mes: int, dia: int):
    """Día y mes sin año: si ya pasó este año, se asume el siguiente."""
    f = _fecha_valida(hoy.year, mes, dia)
    if f and f < hoy:
        f = _fecha_valida(hoy.year + 1, mes, dia)
    return f


def detectar_fecha(texto: str, hoy: date | None = None):
    hoy = hoy or date.today()
    t = FRANJA_MANANA_RE.sub(" ", texto)

    if re.search(r"\bpasado manana\b", t):
        return hoy + timedelta(days=2)
    if re.search(r"\bhoy\b|\besta (?:manana|tarde|noche)\b", t):
        return hoy
    if re.search(r"\bmanana\b", t):
        return hoy + timedelta(days=1)

    # "en 3 dias", "en una semana"
    m = re.search(rf"\ben ({_NUM_RE}|\d{{1,2}}) (dias?|semanas?)\b", t)
    if m:
        n = _a_numero(m.group(1))
        return hoy + timedelta(days=n * (7 if m.group(2).startswith("semana") else 1))

    # "5 de enero", "15 de diciembre de 2027"
    m = re.search(rf"\b(\d{{1,2}}) de ({_MESES_RE})(?: de (\d{{4}}))?\b", t)
    if m:
        dia, mes = int(m.group(1)), MESES[m.group(2)]
        if m.group(3):
            return _fecha_valida(int(m.group(3)), mes, dia)
        return _sin_anio(hoy, mes, dia)

    # "15/12", "15/12/2026"
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
    if m:
        dia, mes = int(m.group(1)), int(m.group(2))
        if m.group(3):
            anio = int(m.group(3))
            return _fecha_valida(anio + 2000 if anio < 100 else anio, mes, dia)
        return _sin_anio(hoy, mes, dia)

    # "el viernes", "este sábado"
    for nombre, indice in DIAS_SEMANA.items():
        if re.search(rf"\b{nombre}\b", t):
            dias_adelante = (indice - hoy.weekday()) % 7
            if dias_adelante == 0:      # si es hoy, se interpreta como la próxima semana
                dias_adelante = 7
            return hoy + timedelta(days=dias_adelante)

    # "el 28" (día del mes, sin confundirlo con "el 3 pm")
    m = re.search(r"\bel (\d{1,2})\b(?!\s*(?:am|pm|:))", t)
    if m:
        dia = int(m.group(1))
        f = _fecha_valida(hoy.year, hoy.month, dia)
        if f is None or f < hoy:
            anio = hoy.year + (1 if hoy.month == 12 else 0)
            f = _fecha_valida(anio, hoy.month % 12 + 1, dia)
        return f

    return None


def _franja(texto: str):
    if re.search(r"\b(?:tarde|noche)\b", texto):
        return "pm"
    if re.search(r"\b(?:por|en|de|a)\s+la\s+manana\b|\besta manana\b|\bmadrugada\b", texto):
        return "am"
    return None


def _ajustar_hora(hora: int, franja, explicito):
    meridiano = explicito or franja
    if meridiano == "pm" and hora < 12:
        return hora + 12
    if meridiano == "am" and hora == 12:
        return 0
    # Sin am/pm: "a las 4" en un salón que abre a las 9 solo puede ser 16:00
    if meridiano is None and 1 <= hora < HORA_MAS_TEMPRANA:
        return hora + 12
    return hora


def detectar_hora(texto: str):
    franja = _franja(texto)

    # 3:30, 3:30pm, 15:00  (va primero para que "9:15pm" no se lea como "15pm")
    m = re.search(r"\b(\d{1,2}):([0-5]\d)(?!\d)\s*(am|pm)?", texto)
    if m:
        hora = _ajustar_hora(int(m.group(1)), franja, m.group(3))
        return time(hora, int(m.group(2))) if 0 <= hora <= 23 else None

    # 3pm, 3 pm, 11am
    m = re.search(r"\b(\d{1,2})\s*(am|pm)\b", texto)
    if m:
        hora = _ajustar_hora(int(m.group(1)), franja, m.group(2))
        return time(hora, 0) if 0 <= hora <= 23 else None

    if re.search(r"\bmedio ?dia\b", texto):
        return time(12, 0)

    # a las 4, a las tres y media, a la una
    m = re.search(rf"\ba (?:las|la) (\d{{1,2}}|{_NUM_RE})\b(?: y (media|cuarto))?", texto)
    if m:
        hora = _ajustar_hora(_a_numero(m.group(1)), franja, None)
        minutos = {"media": 30, "cuarto": 15}.get(m.group(2), 0)
        return time(hora, minutos) if 0 <= hora <= 23 else None

    return None



def parse_mensaje(mensaje: str) -> dict:
    texto_normalizado = normalizar(mensaje)

    intencion = detectar_intencion(texto_normalizado)
    servicio = detectar_servicio(texto_normalizado)
    fecha = detectar_fecha(texto_normalizado)
    hora = detectar_hora(texto_normalizado)

    faltante = []

    if intencion == "reservar":
        if not servicio:
            faltante.append("servicio")
        if not fecha:
            faltante.append("fecha")
        if not hora:
            faltante.append("hora")

    return {
        "mensaje_original": mensaje,
        "texto_normalizado": texto_normalizado,
        "intencion": intencion,
        "servicio": servicio,
        "fecha": fecha,
        "hora": hora,
        "faltante": faltante,
    }