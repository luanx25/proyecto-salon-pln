from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_admin_actual
from models import Usuario, Servicio
from templating import render_admin, flash

router = APIRouter(prefix="/admin/servicios", dependencies=[Depends(get_admin_actual)])


def _obtener(db: Session, servicio_id: int) -> Servicio:
    servicio = db.get(Servicio, servicio_id)
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    return servicio


def _validar(db: Session, nombre: str, duracion_min: int, precio: float, excluir_id=None):
    errores = []

    if not nombre:
        errores.append("El nombre es obligatorio.")
    else:
        consulta = db.query(Servicio).filter(Servicio.nombre == nombre)
        if excluir_id:
            consulta = consulta.filter(Servicio.id != excluir_id)
        if consulta.first():
            errores.append("Ya existe un servicio con ese nombre.")

    if not 5 <= duracion_min <= 480:
        errores.append("La duración debe estar entre 5 y 480 minutos.")
    if precio < 0:
        errores.append("El precio no puede ser negativo.")

    return errores


@router.get("")
def lista(request: Request, admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db)):
    servicios = db.query(Servicio).order_by(Servicio.nombre).all()
    return render_admin(request, "admin/servicios/lista.html", admin, "servicios", servicios=servicios)


@router.get("/nuevo")
def nuevo_form(request: Request, admin: Usuario = Depends(get_admin_actual)):
    return render_admin(
        request, "admin/servicios/form.html", admin, "servicios",
        servicio=None, errores=[], datos={"nombre": "", "duracion_min": 30, "precio": 0},
    )


@router.post("/nuevo")
def nuevo(
        request: Request,
        nombre: str = Form(...),
        duracion_min: int = Form(...),
        precio: float = Form(...),
        admin: Usuario = Depends(get_admin_actual),
        db: Session = Depends(get_db),
):
    nombre = nombre.strip().lower()
    errores = _validar(db, nombre, duracion_min, precio)

    if errores:
        return render_admin(
            request, "admin/servicios/form.html", admin, "servicios", status_code=400,
            servicio=None, errores=errores,
            datos={"nombre": nombre, "duracion_min": duracion_min, "precio": precio},
        )

    db.add(Servicio(nombre=nombre, duracion_min=duracion_min, precio=precio, activo=True))
    db.commit()
    flash(request, f"Servicio '{nombre}' creado. Asígnalo a un empleado para poder reservarlo.", "warn")
    return RedirectResponse("/admin/servicios", status_code=303)


@router.get("/{servicio_id}/editar")
def editar_form(
        servicio_id: int, request: Request,
        admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db),
):
    servicio = _obtener(db, servicio_id)
    return render_admin(
        request, "admin/servicios/form.html", admin, "servicios",
        servicio=servicio, errores=[],
        datos={"nombre": servicio.nombre, "duracion_min": servicio.duracion_min, "precio": servicio.precio},
    )


@router.post("/{servicio_id}/editar")
def editar(
        servicio_id: int, request: Request,
        nombre: str = Form(...),
        duracion_min: int = Form(...),
        precio: float = Form(...),
        admin: Usuario = Depends(get_admin_actual),
        db: Session = Depends(get_db),
):
    servicio = _obtener(db, servicio_id)
    nombre = nombre.strip().lower()
    errores = _validar(db, nombre, duracion_min, precio, excluir_id=servicio.id)

    if errores:
        return render_admin(
            request, "admin/servicios/form.html", admin, "servicios", status_code=400,
            servicio=servicio, errores=errores,
            datos={"nombre": nombre, "duracion_min": duracion_min, "precio": precio},
        )

    servicio.nombre = nombre
    servicio.duracion_min = duracion_min
    servicio.precio = precio
    db.commit()
    flash(request, "Servicio actualizado.")
    return RedirectResponse("/admin/servicios", status_code=303)


@router.post("/{servicio_id}/activar")
def alternar_activo(servicio_id: int, request: Request, db: Session = Depends(get_db)):
    servicio = _obtener(db, servicio_id)
    servicio.activo = not servicio.activo
    db.commit()
    flash(request, f"Servicio '{servicio.nombre}' {'activado' if servicio.activo else 'desactivado'}.")
    return RedirectResponse("/admin/servicios", status_code=303)