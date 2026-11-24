from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_admin_actual
from models import Usuario, SeccionPagina
from sitio import (
    CAMPOS, CAMPOS_POR_TIPO, TIPOS_CON_IMAGEN,
    obtener_config, validar_config, guardar_config,
)
from templating import render_admin, flash

router = APIRouter(prefix="/admin", dependencies=[Depends(get_admin_actual)])

ENLACES_OK = ("/", "#", "https://", "http://")
MAXIMOS = {"titulo": 120, "subtitulo": 200, "contenido": 3000, "boton_texto": 40, "boton_enlace": 300}


def _seccion(db: Session, seccion_id: int) -> SeccionPagina:
    s = db.get(SeccionPagina, seccion_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sección no encontrada.")
    return s


# ---------- Datos generales del salón ----------

@router.get("/sitio")
def sitio_form(request: Request, admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db)):
    return render_admin(
        request, "admin/sitio/config.html", admin, "sitio",
        campos=CAMPOS, datos=obtener_config(db), errores=[],
    )


@router.post("/sitio")
async def sitio_guardar(request: Request, admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db)):
    limpios, errores = validar_config(await request.form())

    if errores:
        return render_admin(
            request, "admin/sitio/config.html", admin, "sitio", status_code=400,
            campos=CAMPOS, datos=limpios, errores=errores,
        )

    guardar_config(db, limpios)
    flash(request, "Datos del salón guardados.")
    return RedirectResponse("/admin/sitio", status_code=303)


# ---------- Secciones ----------

@router.get("/secciones")
def secciones_lista(request: Request, admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db)):
    secciones = db.query(SeccionPagina).order_by(SeccionPagina.orden, SeccionPagina.id).all()
    return render_admin(request, "admin/sitio/secciones.html", admin, "secciones", secciones=secciones)


def _render_editar(request, admin, seccion, datos, errores, status_code=200):
    return render_admin(
        request, "admin/sitio/editar.html", admin, "secciones", status_code=status_code,
        seccion=seccion, datos=datos, errores=errores,
        campos=CAMPOS_POR_TIPO[seccion.tipo],
        con_imagen=seccion.tipo in TIPOS_CON_IMAGEN,
    )


@router.get("/secciones/{seccion_id}/editar")
def editar_form(
        seccion_id: int, request: Request,
        admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db),
):
    s = _seccion(db, seccion_id)
    datos = {c: getattr(s, c) for c in CAMPOS_POR_TIPO[s.tipo]}
    return _render_editar(request, admin, s, datos, [])


@router.post("/secciones/{seccion_id}/editar")
async def editar(
        seccion_id: int, request: Request,
        admin: Usuario = Depends(get_admin_actual), db: Session = Depends(get_db),
):
    s = _seccion(db, seccion_id)
    form = await request.form()
    campos = CAMPOS_POR_TIPO[s.tipo]
    datos = {c: (form.get(c) or "").strip() for c in campos}
    errores = []

    if not datos.get("titulo"):
        errores.append("El título es obligatorio.")
    for c, valor in datos.items():
        if len(valor) > MAXIMOS[c]:
            errores.append(f"'{c}' no puede superar {MAXIMOS[c]} caracteres.")

    if "boton_texto" in datos:
        texto, enlace = datos["boton_texto"], datos["boton_enlace"]
        if bool(texto) != bool(enlace):
            errores.append("El botón necesita texto y enlace, o ambos vacíos.")
        if enlace and (not enlace.startswith(ENLACES_OK) or enlace.startswith("//")):
            errores.append("El enlace debe empezar con #, /, http:// o https://")

    if errores:
        return _render_editar(request, admin, s, datos, errores, status_code=400)

    for c, valor in datos.items():
        setattr(s, c, valor)
    db.commit()
    flash(request, "Sección actualizada.")
    return RedirectResponse("/admin/secciones", status_code=303)