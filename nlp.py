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


def normalizar(texto: str) -> str:
    texto = texto.lower()

    # Quita acentos y convierte ñ en n para simplificar el procesamiento.
    texto = "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )

    # Deja letras, números, espacios y dos puntos.
    texto = re.sub(r"[^a-z0-9\s:]", "", texto)
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


def detectar_fecha(texto: str):
    hoy = date.today()

    if "pasado manana" in texto:
        return hoy + timedelta(days=2)

    if "manana" in texto:
        return hoy + timedelta(days=1)

    if "hoy" in texto:
        return hoy

    dias = {
        "lunes": 0,
        "martes": 1,
        "miercoles": 2,
        "jueves": 3,
        "viernes": 4,
        "sabado": 5,
        "domingo": 6,
    }

    for dia, indice in dias.items():
        if dia in texto:
            dias_adelante = (indice - hoy.weekday()) % 7

            # Si el día es hoy, se interpreta como próxima semana.
            if dias_adelante == 0:
                dias_adelante = 7

            return hoy + timedelta(days=dias_adelante)

    return None


def detectar_hora(texto: str):
    # Caso: 3pm, 3 pm, 11am
    m = re.search(r"(\d{1,2})\s*(am|pm)", texto)
    if m:
        hora = int(m.group(1))
        minutos = 0

        if m.group(2) == "pm" and hora < 12:
            hora += 12

        if m.group(2) == "am" and hora == 12:
            hora = 0

        if 0 <= hora <= 23:
            return time(hora, minutos)

    # Caso: 15:00, 3:30, 3:30pm
    m = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", texto)
    if m:
        hora = int(m.group(1))
        minutos = int(m.group(2))
        meridiano = m.group(3)

        if meridiano == "pm" and hora < 12:
            hora += 12

        if meridiano == "am" and hora == 12:
            hora = 0

        if 0 <= hora <= 23 and 0 <= minutos <= 59:
            return time(hora, minutos)

    # Caso: a las 3, a las 15
    m = re.search(r"a las (\d{1,2})", texto)
    if m:
        hora = int(m.group(1))

        # Si dice tarde o noche, se asume PM para horas menores a 12.
        if re.search(r"tarde|noche", texto) and hora < 12:
            hora += 12

        if 0 <= hora <= 23:
            return time(hora, 0)

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