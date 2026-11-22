from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario
from security import verificar_password

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if request.session.get("usuario_id"):
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(request, "admin/login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    usuario = (
        db.query(Usuario)
        .filter(Usuario.email == email.strip().lower(), Usuario.activo == True)
        .first()
    )

    if not usuario or not verificar_password(password, usuario.password_hash):
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {"error": "Correo o contraseña incorrectos."},
            status_code=401,
        )

    request.session.clear()
    request.session["usuario_id"] = usuario.id
    return RedirectResponse("/admin", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)