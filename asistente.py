from datetime import datetime
from types import SimpleNamespace

from sqlalchemy.orm import Session

import dialogo
from gcal import sincronizar_cita
from models import Servicio
from nlp import parse_mensaje
from services import (
    asignar_empleado_disponible, buscar_servicio, citas_futuras_cliente, crear_cita,
    listar_horarios_disponibles, puede_reservar, validar_contacto,
)
DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

AYUDA = (
    "Puedo ayudarte a reservar una cita y decirte precios. "
    "Por ejemplo: «Quiero una manicura mañana a las 4 pm»."
)


# ---------- utilidades ----------

def _r(texto: str, estado: str = "info", **extra) -> dict:
    """estado: info | pregunta | completo."""
    return {
        "ok": estado == "completo",
        "estado": estado,
        "respuesta": texto,
        "mensaje": texto,       # alias para el widget anterior
        **extra,
    }


def _fmt(dt: datetime) -> str:
    return f"{DIAS_ES[dt.weekday()]} {dt.day}/{dt.month} a las {dt.strftime('%H:%M')}"


def _entendido(estado: dict) -> str:
    partes = []
    if estado["servicio"]:
        partes.append(estado["servicio"])
    if estado["fecha"]:
        f = estado["fecha"]
        partes.append(f"{DIAS_ES[f.weekday()]} {f.day}/{f.month}")
    if estado["hora"]:
        partes.append(estado["hora"].strftime("%H:%M"))
    return f"Entendido: {', '.join(partes)}. " if partes else ""


def _analisis_publico(a: dict) -> dict:
    return {
        "texto_normalizado": a["texto_normalizado"],
        "intencion": a["intencion"],
        "servicio": a["servicio"],
        "fecha": a["fecha"].isoformat() if a["fecha"] else None,
        "hora": a["hora"].strftime("%H:%M") if a["hora"] else None,
        "cita_id": a["cita_id"],
    }


def _cita_json(cita) -> dict:
    return {
        "id": cita.id,
        "servicio": cita.servicio.nombre,
        "fecha_hora": cita.fecha_hora.isoformat(),
        "empleado": cita.empleado.nombre,
        "estado": cita.estado,
    }


def _preguntar(sesion, estado: dict, campo: str, texto: str, con_resumen: bool = True) -> dict:
    estado["esperando"] = campo
    dialogo.guardar(sesion, estado)
    prefijo = _entendido(estado) if con_resumen else ""
    return _r(prefijo + texto, estado="pregunta", esperando=campo)

def _exigir_contacto(sesion, estado: dict, ctx):
    ok, motivo = validar_contacto(ctx.email, ctx.telefono)
    if ok:
        return None
    return _preguntar(
        sesion, estado, "contacto",
        f"{motivo} Complétalo arriba y escribe «listo» para continuar.",
    )


# ---------- manejadores ----------

def _cotizar(analisis: dict, servicios: list) -> dict:
    if not servicios:
        return _r("Por ahora no hay servicios disponibles.")

    elegido = next((s for s in servicios if s.nombre == analisis["servicio"]), None)
    if elegido:
        return _r(f"{elegido.nombre.capitalize()} cuesta ${elegido.precio:,.2f} y dura {elegido.duracion_min} min.")

    detalle = "; ".join(f"{s.nombre} ${s.precio:,.2f} ({s.duracion_min} min)" for s in servicios)
    return _r(f"Estos son nuestros servicios: {detalle}.")


def _reservar(db: Session, sesion, estado: dict, ctx) -> dict:
    servicio = buscar_servicio(db, estado["servicio"]) if estado["servicio"] else None
    if not servicio:
        estado["servicio"] = None
        lista = ", ".join(s.nombre for s in ctx.servicios)
        return _preguntar(sesion, estado, "servicio", f"¿Qué servicio quieres? Tenemos: {lista}.")

    if not estado["fecha"]:
        return _preguntar(sesion, estado, "fecha", "¿Para qué día la quieres?")
    if not estado["hora"]:
        return _preguntar(sesion, estado, "hora", "¿A qué hora?")

    pedido = _exigir_contacto(sesion, estado, ctx)
    if pedido:
        return pedido

    ok, motivo = puede_reservar(db, ctx.email, ctx.telefono)
    if not ok:
        dialogo.limpiar(sesion)
        return _r(motivo)

    fecha_hora = datetime.combine(estado["fecha"], estado["hora"])
    empleado, motivo = asignar_empleado_disponible(db, servicio, fecha_hora)

    if not empleado:
        libres = listar_horarios_disponibles(db, servicio, estado["fecha"])
        if libres:
            estado["hora"] = None
            return _preguntar(
                sesion, estado, "hora",
                f"{motivo} Ese día tengo libre: {', '.join(libres[:6])}. ¿Cuál prefieres?",
            )
        estado["fecha"] = None
        estado["hora"] = None
        return _preguntar(sesion, estado, "fecha", f"{motivo} Ese día ya no hay horarios. ¿Probamos otro día?")

    cita = crear_cita(db, servicio, empleado, fecha_hora, ctx.email, ctx.telefono, ctx.mensaje, origen="chat")
    sincronizar_cita(db, cita)
    dialogo.limpiar(sesion)

    return _r(
        f"¡Listo! Tu cita de {servicio.nombre} quedó para el {_fmt(fecha_hora)} con {empleado.nombre}. "
        f"Tu número de cita es {cita.id}.",
        estado="completo",
        cita=_cita_json(cita),
        atendido_por=empleado.nombre,
    )


def _lista_citas(citas: list) -> str:
    return "; ".join(f"#{c.id} {c.servicio.nombre}, {_fmt(c.fecha_hora)}" for c in citas)


def _elegir_cita(sesion, estado: dict, citas: list, accion: str, filtrar_por_fecha: bool = False):
    """Devuelve (cita, None) si ya sabemos cuál, o (None, respuesta) si hay que contestar algo."""
    if not citas:
        dialogo.limpiar(sesion)
        return None, _r("No encontré citas próximas con esos datos.")

    if estado["cita_id"]:
        cita = next((c for c in citas if c.id == estado["cita_id"]), None)
        if cita:
            return cita, None
        estado["cita_id"] = None
        return None, _preguntar(
            sesion, estado, "cita",
            f"No encontré esa cita entre las tuyas. Tus citas próximas: {_lista_citas(citas)}. "
            f"¿Cuál quieres {accion}? Dime el número.",
            con_resumen=False,
        )

    if filtrar_por_fecha and estado.get("fecha"):
        del_dia = [c for c in citas if c.fecha_hora.date() == estado["fecha"]]
        if del_dia:
            citas = del_dia

    if len(citas) == 1:
        estado["cita_id"] = citas[0].id
        return citas[0], None

    return None, _preguntar(
        sesion, estado, "cita",
        f"Tienes varias citas: {_lista_citas(citas)}. ¿Cuál quieres {accion}? Dime el número.",
        con_resumen=False,
    )


def _consultar(db: Session, sesion, estado: dict, ctx) -> dict:
    pedido = _exigir_contacto(sesion, estado, ctx)
    if pedido:
        return pedido

    citas = citas_futuras_cliente(db, ctx.email, ctx.telefono)
    dialogo.limpiar(sesion)

    if not citas:
        return _r("No tienes citas próximas con esos datos.")
    return _r(f"Tus próximas citas: {_lista_citas(citas)}.")


def _cancelar(db: Session, sesion, estado: dict, ctx) -> dict:
    pedido = _exigir_contacto(sesion, estado, ctx)
    if pedido:
        return pedido

    citas = citas_futuras_cliente(db, ctx.email, ctx.telefono)
    cita, respuesta = _elegir_cita(sesion, estado, citas, "cancelar", filtrar_por_fecha=True)
    if respuesta:
        return respuesta

    if not (estado["esperando"] == "confirmar" and estado["afirmo"]):
        return _preguntar(
            sesion, estado, "confirmar",
            f"¿Confirmas que quieres cancelar tu cita #{cita.id} de {cita.servicio.nombre} "
            f"del {_fmt(cita.fecha_hora)}? Responde «sí» o «no».",
            con_resumen=False,
        )

    cita.estado = "cancelada"
    db.commit()
    sincronizar_cita(db, cita)
    dialogo.limpiar(sesion)

    return _r(
        f"Listo, cancelé tu cita #{cita.id} de {cita.servicio.nombre} del {_fmt(cita.fecha_hora)}.",
        estado="completo",
        cita=_cita_json(cita),
    )


def _reprogramar(db: Session, sesion, estado: dict, ctx) -> dict:
    pedido = _exigir_contacto(sesion, estado, ctx)
    if pedido:
        return pedido

    citas = citas_futuras_cliente(db, ctx.email, ctx.telefono)
    cita, respuesta = _elegir_cita(sesion, estado, citas, "mover")
    if respuesta:
        return respuesta

    if not estado["fecha"]:
        return _preguntar(sesion, estado, "fecha", f"¿Para qué día quieres mover tu cita #{cita.id}?")
    if not estado["hora"]:
        return _preguntar(sesion, estado, "hora", "¿A qué hora?")

    nueva = datetime.combine(estado["fecha"], estado["hora"])
    empleado, motivo = asignar_empleado_disponible(
        db, cita.servicio, nueva, excluir_cita_id=cita.id, preferido=cita.empleado
    )

    if not empleado:
        libres = listar_horarios_disponibles(db, cita.servicio, estado["fecha"], excluir_cita_id=cita.id)
        if libres:
            estado["hora"] = None
            return _preguntar(
                sesion, estado, "hora",
                f"{motivo} Ese día tengo libre: {', '.join(libres[:6])}. ¿Cuál prefieres?",
            )
        estado["fecha"] = None
        estado["hora"] = None
        return _preguntar(sesion, estado, "fecha", f"{motivo} Ese día ya no hay horarios. ¿Probamos otro día?")

    cita.fecha_hora = nueva
    cita.empleado_id = empleado.id
    db.commit()
    db.refresh(cita)
    sincronizar_cita(db, cita)
    dialogo.limpiar(sesion)

    return _r(
        f"Listo, moví tu cita #{cita.id} de {cita.servicio.nombre} al {_fmt(nueva)} con {empleado.nombre}.",
        estado="completo",
        cita=_cita_json(cita),
        atendido_por=empleado.nombre,
    )


MANEJADORES = {
    "reservar": _reservar,
    "cancelar": _cancelar,
    "reprogramar": _reprogramar,
    "consultar": _consultar,
}

# ---------- punto de entrada ----------

def _despachar(db, sesion, analisis: dict, email: str, telefono: str, servicios: list) -> dict:
    intencion = analisis["intencion"]
    pendiente = dialogo.cargar(sesion)
    ctx = SimpleNamespace(email=email, telefono=telefono, mensaje=analisis["mensaje_original"], servicios=servicios)

    if intencion == "abortar":
        dialogo.limpiar(sesion)
        return _r("Sin problema, lo dejamos aquí. Cuando quieras retomarlo, escríbeme.")
    if intencion == "saludo":
        return _r("¡Hola! " + AYUDA)
    if intencion == "cotizar":                      # responde sin perder el trámite pendiente
        return _cotizar(analisis, servicios)
    if intencion in ("ayuda", "afirmar") and not pendiente:
        return _r("No estoy seguro de haberte entendido. " + AYUDA)

    estado = dialogo.fusionar(pendiente, analisis)
    manejador = MANEJADORES.get(estado["intencion"])
    if not manejador:
        return _r("Esa gestión todavía no está disponible en el chat. " + AYUDA)

    return manejador(db, sesion, estado, ctx)


def procesar_mensaje(db: Session, sesion, mensaje: str, email: str, telefono: str) -> dict:
    servicios = db.query(Servicio).filter(Servicio.activo == True).order_by(Servicio.nombre).all()
    analisis = parse_mensaje(mensaje, nombres_servicios=[s.nombre for s in servicios])

    resultado = _despachar(db, sesion, analisis, email, telefono, servicios)
    resultado["analisis"] = _analisis_publico(analisis)
    return resultado