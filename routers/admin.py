from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_admin_actual
from models import Usuario, Cita, Servicio, Empleado
from templating import render_admin

router = APIRouter(prefix="/admin", dependencies=[Depends(get_admin_actual)])


@router.get("")
def dashboard(
        request: Request,
        admin: Usuario = Depends(get_admin_actual),
        db: Session = Depends(get_db),
):
    ahora = datetime.now()
    inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    activas = Cita.estado != "cancelada"

    citas_hoy = db.query(Cita).filter(
        activas, Cita.fecha_hora >= inicio_hoy, Cita.fecha_hora < inicio_hoy + timedelta(days=1)
    ).count()

    citas_semana = db.query(Cita).filter(
        activas, Cita.fecha_hora >= ahora, Cita.fecha_hora < ahora + timedelta(days=7)
    ).count()

    proximas = (
        db.query(Cita)
        .filter(activas, Cita.fecha_hora >= ahora)
        .order_by(Cita.fecha_hora)
        .limit(5)
        .all()
    )

    return render_admin(
        request, "admin/dashboard.html", admin, "dashboard",
        citas_hoy=citas_hoy,
        citas_semana=citas_semana,
        servicios_activos=db.query(Servicio).filter(Servicio.activo == True).count(),
        empleados_activos=db.query(Empleado).filter(Empleado.activo == True).count(),
        proximas=proximas,
    )