from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import asistente
from database import get_db
from models import Servicio, Empleado
from schemas import MensajeEntrada
from services import (
    listar_horarios_disponibles
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
@router.post("/landing/message")
def procesar_mensaje_landing(datos: MensajeEntrada, request: Request, db: Session = Depends(get_db)):
    return asistente.procesar_mensaje(
        db,
        request.session,
        datos.mensaje,
        datos.cliente_email.strip().lower(),
        datos.cliente_telefono.strip(),
    )


