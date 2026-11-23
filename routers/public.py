from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
from models import SeccionPagina, Servicio, Empleado
from sitio import obtener_config
from templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def landing(request: Request, db: Session = Depends(get_db)):
    secciones = (
        db.query(SeccionPagina)
        .filter(SeccionPagina.visible == True)
        .order_by(SeccionPagina.orden, SeccionPagina.id)
        .all()
    )
    return templates.TemplateResponse(request, "index.html", {
        "config": obtener_config(db),
        "secciones": secciones,
        "servicios": db.query(Servicio).filter(Servicio.activo == True).order_by(Servicio.nombre).all(),
        "empleados": db.query(Empleado).filter(Empleado.activo == True).order_by(Empleado.nombre).all(),
    })