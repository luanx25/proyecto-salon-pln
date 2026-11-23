from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_admin_actual
from models import Usuario, Empleado, Servicio, HorarioEmpleado, Cita
from templating import render_admin, flash

router = APIRouter(prefix="/admin/empleados", dependencies=[Depends(get_admin_actual)])

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _obtener(db: Session, empleado_id: int) -> Empleado:
    emp = db.get(Empleado, empleado_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    return emp


def _datos_vacios():
    return {
        "nombre": "",
        "activo": True,
        "servicios": set(),
        "horarios": {d: ("10:00", "19:00") for d in range(6)},  # lunes a sábado
    }


def _datos_desde_empleado(emp: Empleado):
    return {
        "nombre": emp.nombre,
        "activo": emp.activo,
        "servicios": {s.id for s in emp.servicios},
        "horarios": {
            h.dia_semana: (h.hora_inicio.strftime("%H:%M"), h.hora_fin.strftime("%H:%M"))
            for h in emp.horarios
        },
    }


def _leer_formulario(form):
    datos = {
        "nombre": form.get("nombre", "").strip(),
        "activo": form.get("activo") == "on",
        "servicios": {int(x) for x in form.getlist("servicios") if x.isdigit()},
        "horarios": {},
    }
    errores = []

    for dia in range(7):
        if form.get(f"dia_{dia}") != "on":
            continue
        ini_txt = form.get(f"inicio_{dia}", "")
        fin_txt = form.get(f"fin_{dia}", "")
        datos["horarios"][dia] = (ini_txt, fin_txt)
        try:
            ini = time.fromisoformat(ini_txt)
            fin = time.fromisoformat(fin_txt)
        except ValueError:
            errores.append(f"{DIAS[dia]}: las horas no son válidas.")
            continue
        if ini >= fin:
            errores.append(f"{DIAS[dia]}: la hora de salida debe ser posterior a la de entrada.")

    return datos, errores


def _validar(db: Session, datos, errores, excluir_id=None):
    if not datos["nombre"]:
        errores.append("El nombre es obligatorio.")
    else:
        consulta = db.query(Empleado).filter(Empleado.nombre == datos["nombre"])
        if excluir_id:
            consulta = consulta.filter(Empleado.id != excluir_id)
        if consulta.first():
            errores.append("Ya existe un empleado con ese nombre.")
    return errores


def _aplicar(db: Session, emp: Empleado, datos):
    emp.nombre = datos["nombre"]
    emp.activo = datos["activo"]

    ids = datos["servicios"]
    emp.servicios = db.query(Servicio).filter(Servicio.id.in_(ids)).all() if ids else []

    emp.horarios.clear()
    db.flush()
    for dia, (ini, fin) in datos["horarios"].items():
        emp.horarios.append(
            HorarioEmpleado(
                dia_semana=dia,
                hora_inicio=time.fromisoformat(ini),
                hora_fin=time.fromisoformat(fin),
            )
        )


def _render_form(request, admin, db, emp, datos, errores, status_code=200):
    return render_admin(
        request, "admin/empleados/form.html", admin, "empleados", status_code=status_code,
        empleado=emp, datos=datos, errores=errores, dias=DIAS,
        servicios=db.query(Servicio).order_by(Servicio.nombre).all(),
    )


@router.get("")
def lista(request: Request, admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db)):
    empleados = db.query(Empleado).order_by(Empleado.nombre).all()
    return render_admin(request, "admin/empleados/lista.html", admin, "empleados", empleados=empleados)


@router.get("/nuevo")
def nuevo_form(request: Request, admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db)):
    return _render_form(request, admin, db, None, _datos_vacios(), [])


@router.post("/nuevo")
async def nuevo(request: Request, admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db)):
    datos, errores = _leer_formulario(await request.form())
    _validar(db, datos, errores)

    if errores:
        return _render_form(request, admin, db, None, datos, errores, status_code=400)

    emp = Empleado(nombre=datos["nombre"])
    db.add(emp)
    _aplicar(db, emp, datos)
    db.commit()
    flash(request, f"Empleado '{emp.nombre}' creado.")
    return RedirectResponse("/admin/empleados", status_code=303)


@router.get("/{empleado_id}/editar")
def editar_form(
        empleado_id: int, request: Request,
        admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db),
):
    emp = _obtener(db, empleado_id)
    return _render_form(request, admin, db, emp, _datos_desde_empleado(emp), [])


@router.post("/{empleado_id}/editar")
async def editar(
        empleado_id: int, request: Request,
        admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db),
):
    emp = _obtener(db, empleado_id)
    datos, errores = _leer_formulario(await request.form())
    _validar(db, datos, errores, excluir_id=emp.id)

    if errores:
        return _render_form(request, admin, db, emp, datos, errores, status_code=400)

    _aplicar(db, emp, datos)
    db.commit()
    flash(request, "Empleado actualizado.")
    return RedirectResponse("/admin/empleados", status_code=303)


@router.post("/{empleado_id}/activar")
def alternar_activo(empleado_id: int, request: Request, db: Session = Depends(get_db)):
    emp = _obtener(db, empleado_id)
    emp.activo = not emp.activo
    db.commit()

    if emp.activo:
        flash(request, f"'{emp.nombre}' activado.")
    else:
        pendientes = db.query(Cita).filter(
            Cita.empleado_id == emp.id,
            Cita.estado == "confirmada",
            Cita.fecha_hora >= datetime.now(),
            ).count()
        if pendientes:
            flash(
                request,
                f"'{emp.nombre}' desactivado, pero tiene {pendientes} cita(s) futuras confirmadas. "
                "Reprográmalas desde la sección Citas.",
                "warn",
            )
        else:
            flash(request, f"'{emp.nombre}' desactivado.")

    return RedirectResponse("/admin/empleados", status_code=303)