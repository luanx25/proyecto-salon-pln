import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
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
from uploads import guardar_imagen, borrar_imagen

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
        sec=seccion, datos=datos, errores=errores,
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

@router.post("/secciones/{seccion_id}/imagen")
async def subir_imagen(
        seccion_id: int, request: Request,
        archivo: UploadFile | None = File(None), db: Session = Depends(get_db),
):
    s = _seccion(db, seccion_id)
    destino = f"/admin/secciones/{s.id}/editar"

    if s.tipo not in TIPOS_CON_IMAGEN:
        raise HTTPException(status_code=400, detail="Esta sección no admite imagen.")
    if not archivo or not archivo.filename:
        flash(request, "Elige un archivo.", "error")
        return RedirectResponse(destino, status_code=303)

    try:
        nueva = await guardar_imagen(archivo)
    except ValueError as e:
        flash(request, str(e), "error")
        return RedirectResponse(destino, status_code=303)

    borrar_imagen(s.imagen)
    s.imagen = nueva
    db.commit()
    flash(request, "Imagen actualizada.")
    return RedirectResponse(destino, status_code=303)


@router.post("/secciones/{seccion_id}/imagen/quitar")
def quitar_imagen(seccion_id: int, request: Request, db: Session = Depends(get_db)):
    s = _seccion(db, seccion_id)
    borrar_imagen(s.imagen)
    s.imagen = None
    db.commit()
    flash(request, "Imagen eliminada.")
    return RedirectResponse(f"/admin/secciones/{s.id}/editar", status_code=303)


@router.post("/secciones/{seccion_id}/mover")
def mover(seccion_id: int, direccion: str = Form(...), db: Session = Depends(get_db)):
    todas = db.query(SeccionPagina).order_by(SeccionPagina.orden, SeccionPagina.id).all()
    idx = next((i for i, s in enumerate(todas) if s.id == seccion_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Sección no encontrada.")

    destino = idx - 1 if direccion == "subir" else idx + 1
    if 0 <= destino < len(todas):
        todas[idx], todas[destino] = todas[destino], todas[idx]
        for i, s in enumerate(todas):   # renumera para evitar empates
            s.orden = i
        db.commit()

    return RedirectResponse("/admin/secciones", status_code=303)


@router.post("/secciones/{seccion_id}/visibilidad")
def alternar_visibilidad(seccion_id: int, request: Request, db: Session = Depends(get_db)):
    s = _seccion(db, seccion_id)
    s.visible = not s.visible
    db.commit()

    if s.tipo == "reserva" and not s.visible:
        flash(request, "Ocultaste la sección de reservas: los clientes ya no podrán agendar desde la página.", "warn")
    else:
        flash(request, f"Sección {'visible' if s.visible else 'oculta'}.")
    return RedirectResponse("/admin/secciones", status_code=303)


@router.post("/secciones/nueva")
def nueva(request: Request, db: Session = Depends(get_db)):
    ultimo = db.query(SeccionPagina).order_by(SeccionPagina.orden.desc()).first()
    s = SeccionPagina(
        clave=f"texto-{uuid.uuid4().hex[:8]}",
        tipo="texto",
        titulo="Nueva sección",
        orden=(ultimo.orden + 1) if ultimo else 0,
        visible=False,   # oculta hasta que el admin la complete
    )
    db.add(s)
    db.commit()
    flash(request, "Sección creada y oculta. Complétala y actívala cuando esté lista.", "warn")
    return RedirectResponse(f"/admin/secciones/{s.id}/editar", status_code=303)


@router.post("/secciones/{seccion_id}/eliminar")
def eliminar(seccion_id: int, request: Request, db: Session = Depends(get_db)):
    s = _seccion(db, seccion_id)
    if s.tipo != "texto":
        flash(request, "Solo se pueden eliminar secciones de texto. Las demás puedes ocultarlas.", "error")
        return RedirectResponse("/admin/secciones", status_code=303)

    borrar_imagen(s.imagen)
    db.delete(s)
    db.commit()
    flash(request, "Sección eliminada.")
    return RedirectResponse("/admin/secciones", status_code=303)