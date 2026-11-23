import re

from models import ConfiguracionSitio
from services import EMAIL_REGEX

CONFIG_DEFAULTS = {
    "nombre_salon": "Mi Salón de Belleza",
    "telefono": "",
    "email": "",
    "direccion": "",
    "horario_texto": "Lunes a sábado de 10:00 a 19:00",
    "whatsapp": "",
    "instagram": "",
    "facebook": "",
    "color_principal": "#b5446e",
}

# (clave, etiqueta, tipo de input)
CAMPOS = [
    ("nombre_salon", "Nombre del salón", "text"),
    ("telefono", "Teléfono", "text"),
    ("email", "Correo de contacto", "email"),
    ("direccion", "Dirección", "text"),
    ("horario_texto", "Horario (texto visible en la página)", "text"),
    ("whatsapp", "WhatsApp (con código de país, solo números)", "text"),
    ("instagram", "Instagram (URL completa)", "text"),
    ("facebook", "Facebook (URL completa)", "text"),
    ("color_principal", "Color principal", "color"),
]

LIMITES = {"nombre_salon": 80, "telefono": 30, "email": 120, "direccion": 200,
           "horario_texto": 120, "instagram": 200, "facebook": 200}

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# Qué campos de texto edita el admin en cada tipo de sección
CAMPOS_POR_TIPO = {
    "hero": ["titulo", "subtitulo", "boton_texto", "boton_enlace"],
    "texto": ["titulo", "contenido"],
    "servicios": ["titulo", "subtitulo"],
    "equipo": ["titulo", "subtitulo"],
    "reserva": ["titulo", "subtitulo"],
    "contacto": ["titulo", "subtitulo"],
}
TIPOS_CON_IMAGEN = {"hero", "texto"}


def obtener_config(db):
    guardados = {c.clave: c.valor for c in db.query(ConfiguracionSitio).all()}
    return {**CONFIG_DEFAULTS, **guardados}


def validar_config(datos):
    limpios = {k: (datos.get(k) or "").strip() for k in CONFIG_DEFAULTS}
    errores = []

    for clave, maximo in LIMITES.items():
        if len(limpios[clave]) > maximo:
            errores.append(f"'{clave}' no puede superar {maximo} caracteres.")

    if not limpios["nombre_salon"]:
        errores.append("El nombre del salón es obligatorio.")
    if limpios["email"] and not EMAIL_REGEX.match(limpios["email"]):
        errores.append("El correo de contacto no es válido.")
    if not HEX.match(limpios["color_principal"]):
        errores.append("El color debe tener formato #rrggbb.")

    if limpios["whatsapp"]:
        digitos = re.sub(r"\D", "", limpios["whatsapp"])
        if not 8 <= len(digitos) <= 15:
            errores.append("El WhatsApp debe tener entre 8 y 15 dígitos.")
        limpios["whatsapp"] = digitos

    for red in ("instagram", "facebook"):
        if limpios[red] and not limpios[red].startswith("https://"):
            errores.append(f"El enlace de {red} debe empezar con https://")

    return limpios, errores


def guardar_config(db, limpios):
    for clave, valor in limpios.items():
        fila = db.get(ConfiguracionSitio, clave)
        if fila:
            fila.valor = valor
        else:
            db.add(ConfiguracionSitio(clave=clave, valor=valor))
    db.commit()