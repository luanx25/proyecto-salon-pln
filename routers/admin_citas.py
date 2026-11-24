from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from constantes import ESTADOS_CITA
from database import get_db
from dependencies import get_admin_actual
from models import Usuario, Cita, Empleado
from services import validar_disponibilidad
from templating import render_admin, flash
from gcal import gcal_habilitado, sincronizar_cita

router = APIRouter(prefix="/admin/citas", dependencies=[Depends(get_admin_actual)])


def _obtener(db: Session, cita_id: int) -> Cita:
    cita = db.get(Cita, cita_id)
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada.")
    return cita

def _avisar_si_fallo(request: Request, resultado: str):
    if resultado == "error":
        flash(
            request,
            "El cambio se guardó, pero no se pudo actualizar Google Calendar. "
            "Usa el botón «Sincronizar» de esta cita para reintentar.",
            "warn",
        )


def _render_detalle(request, admin, cita, errores=None, status_code=200):
    candidatos = [e for e in cita.servicio.empleados if e.activo]
    return render_admin(
        request, "admin/citas/detalle.html", admin, "citas", status_code=status_code,
        cita=cita, candidatos=candidatos, errores=errores or [],
        gcal_on=gcal_habilitado(),
    )


@router.get("")
def lista(
        request: Request, estado: str = "", fecha: str = "",
        admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db),
):
    consulta = db.query(Cita)

    if estado in ESTADOS_CITA:
        consulta = consulta.filter(Cita.estado == estado)
    else:
        estado = ""

    try:
        dia = date.fromisoformat(fecha) if fecha else None
    except ValueError:
        dia = None
    if dia:
        inicio = datetime.combine(dia, time.min)
        consulta = consulta.filter(Cita.fecha_hora >= inicio, Cita.fecha_hora < inicio + timedelta(days=1))
    else:
        fecha = ""

    citas = consulta.order_by(Cita.fecha_hora.desc()).limit(200).all()
    return render_admin(
        request, "admin/citas/lista.html", admin, "citas",
        citas=citas, estado=estado, fecha=fecha,
    )


@router.get("/{cita_id}")
def detalle(
        cita_id: int, request: Request,
        admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db),
):
    return _render_detalle(request, admin, _obtener(db, cita_id))


@router.post("/{cita_id}/estado")
def cambiar_estado(
        cita_id: int, request: Request, estado: str = Form(...), db: Session = Depends(get_db),
):
    cita = _obtener(db, cita_id)
    destino = f"/admin/citas/{cita.id}"

    if estado not in ESTADOS_CITA:
        flash(request, "Estado no válido.", "error")
        return RedirectResponse(destino, status_code=303)

    # Reactivar una cita cancelada exige que el horario siga libre
    if cita.estado == "cancelada" and estado == "confirmada":
        ok, mensaje = validar_disponibilidad(
            db, cita.fecha_hora, cita.servicio, cita.empleado, excluir_cita_id=cita.id
        )
        if not ok:
            flash(request, f"No se puede reactivar la cita: {mensaje}", "error")
            return RedirectResponse(destino, status_code=303)

    cita.estado = estado
    db.commit()
    _avisar_si_fallo(request, sincronizar_cita(db, cita))
    flash(request, f"Cita marcada como '{ESTADOS_CITA[estado]}'.")
    return RedirectResponse(destino, status_code=303)


@router.post("/{cita_id}/reprogramar")
def reprogramar(
        cita_id: int, request: Request,
        fecha_hora: str = Form(...), empleado_id: int = Form(...),
        admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db),
):
    cita = _obtener(db, cita_id)

    if cita.estado != "confirmada":
        flash(request, "Solo se pueden reprogramar citas confirmadas.", "error")
        return RedirectResponse(f"/admin/citas/{cita.id}", status_code=303)

    errores = []
    try:
        nueva = datetime.fromisoformat(fecha_hora)
    except ValueError:
        return _render_detalle(request, admin, cita, ["La fecha y hora no son válidas."], 400)

    empleado = db.get(Empleado, empleado_id)
    if not empleado or not empleado.activo or cita.servicio not in empleado.servicios:
        errores.append("Elige un empleado activo que realice este servicio.")
    else:
        ok, mensaje = validar_disponibilidad(db, nueva, cita.servicio, empleado, excluir_cita_id=cita.id)
        if not ok:
            errores.append(mensaje)

    if errores:
        return _render_detalle(request, admin, cita, errores, 400)

    cita.fecha_hora = nueva
    cita.empleado_id = empleado.id
    db.commit()
    _avisar_si_fallo(request, sincronizar_cita(db, cita))
    flash(request, "Cita reprogramada.")
    return RedirectResponse(f"/admin/citas/{cita.id}", status_code=303)

@router.post("/{cita_id}/sincronizar")
def sincronizar(cita_id: int, request: Request, db: Session = Depends(get_db)):
    cita = _obtener(db, cita_id)
    resultado = sincronizar_cita(db, cita)

    if resultado == "ok":
        flash(request, "Cita sincronizada con Google Calendar.")
    elif resultado == "desactivado":
        flash(request, "Google Calendar no está configurado.", "warn")
    else:
        flash(request, "No se pudo sincronizar. Revisa la terminal para ver el detalle.", "error")
    return RedirectResponse(f"/admin/citas/{cita.id}", status_code=303)