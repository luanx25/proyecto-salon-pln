import re
from datetime import datetime, timedelta, date, time
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

def validar_horario_general(fecha_hora: datetime, servicio: Servicio):
    """Valida fecha futura y que el servicio completo quepa en el horario del salón."""
    if fecha_hora < datetime.now():
        return False, "La fecha y hora seleccionadas ya pasaron."

    fin = fecha_hora + timedelta(minutes=servicio.duracion_min)
    apertura = fecha_hora.replace(hour=HORA_APERTURA, minute=0, second=0, microsecond=0)
    cierre = fecha_hora.replace(hour=HORA_CIERRE, minute=0, second=0, microsecond=0)

    if fecha_hora < apertura or fin > cierre:
        return False, (
            f"El horario de atención es de {HORA_APERTURA}:00 a {HORA_CIERRE}:00 "
            f"y '{servicio.nombre}' dura {servicio.duracion_min} min."
        )

    return True, "Horario válido."


def hay_traslape(db: Session, empleado: Empleado, inicio: datetime, fin: datetime, excluir_cita_id: int | None = None):
    """True si el empleado ya tiene una cita que choca con [inicio, fin)."""
    inicio_dia = inicio.replace(hour=0, minute=0, second=0, microsecond=0)

    consulta = db.query(Cita).filter(
        Cita.empleado_id == empleado.id,
        Cita.estado != "cancelada",
        Cita.fecha_hora >= inicio_dia,
        Cita.fecha_hora < inicio_dia + timedelta(days=1),
        )
    if excluir_cita_id is not None:
        consulta = consulta.filter(Cita.id != excluir_cita_id)

    for c in consulta.all():
        c_inicio = c.fecha_hora
        c_fin = c_inicio + timedelta(minutes=c.servicio.duracion_min)
        if inicio < c_fin and fin > c_inicio:
            return True

    return False


def validar_disponibilidad(
        db: Session, fecha_hora: datetime, servicio: Servicio, empleado: Empleado,
        excluir_cita_id: int | None = None,
):
    ok, mensaje = validar_horario_general(fecha_hora, servicio)
    if not ok:
        return False, mensaje

    fin = fecha_hora + timedelta(minutes=servicio.duracion_min)

    if not empleado_trabaja_en(empleado, fecha_hora, fin):
        return False, f"{empleado.nombre} no trabaja en ese horario."

    if hay_traslape(db, empleado, fecha_hora, fin, excluir_cita_id):
        return False, "El horario ya está ocupado. Elige otro horario."

    return True, "Horario disponible."

def empleado_trabaja_en(empleado: Empleado, inicio: datetime, fin: datetime):
    """True si [inicio, fin] cae dentro de algún bloque laboral del empleado ese día."""
    for h in empleado.horarios:
        if h.dia_semana == inicio.weekday():
            if h.hora_inicio <= inicio.time() and fin.time() <= h.hora_fin:
                return True
    return False


def asignar_empleado_disponible(db: Session, servicio: Servicio, fecha_hora: datetime):
    """Devuelve (empleado, mensaje). Si nadie puede, empleado es None."""
    ok, mensaje = validar_horario_general(fecha_hora, servicio)
    if not ok:
        return None, mensaje

    fin = fecha_hora + timedelta(minutes=servicio.duracion_min)

    candidatos = [e for e in servicio.empleados if e.activo]
    if not candidatos:
        return None, f"No hay personal activo que realice '{servicio.nombre}'."

    for empleado in candidatos:
        if not empleado_trabaja_en(empleado, fecha_hora, fin):
            continue
        if hay_traslape(db, empleado, fecha_hora, fin):
            continue
        return empleado, "Horario disponible."

    return None, "No hay personal disponible en ese horario. Elige otro horario."

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

def listar_horarios_disponibles(db: Session, servicio: Servicio, dia: date, paso_min: int = 30):
    """Lista las horas de inicio ('HH:MM') en las que se puede agendar el servicio ese día."""
    horarios = []
    actual = datetime.combine(dia, time(HORA_APERTURA, 0))
    cierre = datetime.combine(dia, time(HORA_CIERRE, 0))

    while actual + timedelta(minutes=servicio.duracion_min) <= cierre:
        empleado, _ = asignar_empleado_disponible(db, servicio, actual)
        if empleado:
            horarios.append(actual.strftime("%H:%M"))
        actual += timedelta(minutes=paso_min)

    return horarios