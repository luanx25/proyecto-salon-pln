from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date
from database import get_db
from models import Servicio, Cita, Empleado
from schemas import MensajeEntrada
from nlp import parse_mensaje
from gcal import sincronizar_cita
from services import (
    validar_contacto,buscar_servicio,  asignar_empleado_disponible, crear_cita,listar_horarios_disponibles
)

router = APIRouter(prefix="/api")

@router.get("/servicios")
def listar_servicios(db: Session = Depends(get_db)):
    servicios = db.query(Servicio).filter(Servicio.activo == True).all()
    
    return [
            {
                "id": s.id,
                "nombre": s.nombre,
                "duracion_min": s.duracion_min,
                "precio": s.precio,
                "activo": s.activo,
            }
            for s in servicios
        ]

@router.get("/empleados")
def listar_empleados(db: Session = Depends(get_db)):
    empleados = db.query(Empleado).filter(Empleado.activo == True).all()

    return [
        {
            "id": e.id,
            "nombre": e.nombre,
            "activo": e.activo,
        }
        for e in empleados
    ]

@router.get("/disponibilidad")
def disponibilidad(fecha: date, servicio_id: int, db: Session = Depends(get_db)):
    servicio = (
        db.query(Servicio)
        .filter(Servicio.id == servicio_id, Servicio.activo == True)
        .first()
    )
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")

    return {
        "fecha": fecha.isoformat(),
        "servicio": servicio.nombre,
        "horarios": listar_horarios_disponibles(db, servicio, fecha),
    }



@router.post("/landing/message")
def procesar_mensaje_landing(payload: MensajeEntrada, db: Session = Depends(get_db)):
    flujo = []

    # Paso 1: mensaje recibido
    flujo.append("1. Mensaje recibido en la landing.")

    # Paso 2: validación de contacto aparte
    flujo.append("2. Se validan email y teléfono del cliente.")

    contacto_valido, mensaje_contacto = validar_contacto(
        payload.cliente_email,
        payload.cliente_telefono
    )

    if not contacto_valido:
        return {
            "ok": False,
            "flujo": flujo,
            "mensaje": mensaje_contacto
        }

    # Paso 3: PLN
    analisis = parse_mensaje(payload.mensaje)
    flujo.append("3. PLN extrae intención, servicio, fecha y hora.")

    analisis_serializable = {
        "intencion": analisis["intencion"],
        "servicio": analisis["servicio"],
        "fecha": analisis["fecha"].isoformat() if analisis["fecha"] else None,
        "hora": analisis["hora"].strftime("%H:%M") if analisis["hora"] else None,
        "faltante": analisis["faltante"],
        "texto_normalizado": analisis["texto_normalizado"],
    }

    # Solo se procesa reservar en esta prueba funcional
    if analisis["intencion"] != "reservar":
        return {
            "ok": False,
            "flujo": flujo,
            "analisis": analisis_serializable,
            "mensaje": "En esta prueba solo se procesa la intención 'reservar'."
        }

    # Si falta información de la reserva
    if analisis["faltante"]:
        return {
            "ok": False,
            "flujo": flujo,
            "analisis": analisis_serializable,
            "mensaje": "Faltan datos para completar la reserva.",
            "faltante": analisis["faltante"]
        }

    # Paso 4: buscar servicio
    flujo.append("4. Sistema busca el servicio en el catálogo.")

    servicio = buscar_servicio(db, analisis["servicio"])

    if not servicio:
        return {
            "ok": False,
            "flujo": flujo,
            "analisis": analisis_serializable,
            "mensaje": f"No se encontró el servicio: {analisis['servicio']}."
        }
       # Paso 5: asignar empleado disponible
    flujo.append("5. Sistema busca a una persona disponible para el servicio.")

    fecha_hora = datetime.combine(analisis["fecha"], analisis["hora"])
    empleado, mensaje_disponibilidad = asignar_empleado_disponible(db, servicio, fecha_hora)

    if not empleado:
        return {
            "ok": False,
            "flujo": flujo,
            "analisis": analisis_serializable,
            "mensaje": mensaje_disponibilidad,
            "fecha_hora_solicitada": fecha_hora.isoformat(),
        }

    # Paso 6: disponibilidad confirmada
    flujo.append("6. Sistema confirma disponibilidad.")


    # Paso 7: guardar cita
    flujo.append("7. Sistema guarda la cita en la tabla 'citas'.")

    cita = crear_cita(
        db=db,
        servicio=servicio,
        empleado=empleado,
        fecha_hora=fecha_hora,
        cliente_email=payload.cliente_email,
        cliente_telefono=payload.cliente_telefono,
        mensaje_original=payload.mensaje
    )
    sincronizar_cita(db, cita)

    # Paso 8: mostrar resultado
    flujo.append("8. La interfaz muestra la confirmación.")

    return {
        "ok": True,
        "flujo": flujo,
        "analisis": analisis_serializable,
        "mensaje": "Cita confirmada correctamente.",
        "cliente": {
            "email": cita.cliente_email,
            "telefono": cita.cliente_telefono,
        },
        "atendido_por": empleado.nombre,
        "cita": {
            "id": cita.id,
            "servicio": servicio.nombre,
            "fecha_hora": cita.fecha_hora.isoformat(),
            "estado": cita.estado,
            "origen": cita.origen,
            "mensaje_original": cita.mensaje_original,
        }
    }







