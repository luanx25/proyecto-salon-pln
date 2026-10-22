import re
from datetime import datetime
from sqlalchemy.orm import Session
from models import Servicio, Cita, Empleado


HORA_APERTURA = 9
HORA_CIERRE = 19

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_contacto(cliente_email: str, cliente_telefono: str):
    if not cliente_email:
        return False, "El correo electrónico es obligatorio."

    if not EMAIL_REGEX.match(cliente_email):
        return False, "El correo electrónico no tiene un formato válido."

    if not cliente_telefono:
        return False, "El número de teléfono es obligatorio."

    telefono_limpio = re.sub(r"\D", "", cliente_telefono)

    if len(telefono_limpio) < 7 or len(telefono_limpio) > 15:
        return False, "El número de teléfono debe tener entre 7 y 15 dígitos."

    return True, "Datos de contacto válidos."


def obtener_empleado_por_nombre(db: Session, nombre: str):
    return (
        db.query(Empleado)
        .filter(
            Empleado.nombre == nombre,
            Empleado.activo == True
        )
        .first()
    )


def obtener_empleado_default(db: Session):
    return (
        db.query(Empleado)
        .filter(Empleado.activo == True)
        .first()
    )


def buscar_servicio(db: Session, nombre_servicio: str):
    return (
        db.query(Servicio)
        .filter(
            Servicio.nombre == nombre_servicio,
            Servicio.activo == True
        )
        .first()
    )


def validar_disponibilidad(db: Session, fecha_hora: datetime):
    ahora = datetime.now()

    if fecha_hora < ahora:
        return False, "La fecha y hora seleccionadas ya pasaron."

    if fecha_hora.hour < HORA_APERTURA or fecha_hora.hour >= HORA_CIERRE:
        return False, f"El horario de atención es de {HORA_APERTURA}:00 a {HORA_CIERRE}:00."

    cita_existente = (
        db.query(Cita)
        .filter(
            Cita.fecha_hora == fecha_hora,
            Cita.estado != "cancelada"
        )
        .first()
    )

    if cita_existente:
        return False, "El horario ya está ocupado. Elige otro horario."

    return True, "Horario disponible."


def crear_cita(
    db: Session,
    servicio: Servicio,
    empleado: Empleado,
    fecha_hora: datetime,
    cliente_email: str,
    cliente_telefono: str,
    mensaje_original: str
):
    telefono_limpio = re.sub(r"\D", "", cliente_telefono)

    cita = Cita(
        servicio_id=servicio.id,
        empleado_id=empleado.id,
        cliente_email=cliente_email,
        cliente_telefono=telefono_limpio,
        mensaje_original=mensaje_original,
        fecha_hora=fecha_hora,
        estado="confirmada",
        origen="landing"
    )

    db.add(cita)
    db.commit()
    db.refresh(cita)

    return cita