from fastapi import Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario


class RedirigirALogin(Exception):
    """Se lanza cuando se intenta entrar al panel sin sesión válida."""


def get_admin_actual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    usuario_id = request.session.get("usuario_id")
    usuario = db.get(Usuario, usuario_id) if usuario_id else None

    if not usuario or not usuario.activo:
        request.session.clear()
        raise RedirigirALogin()

    return usuario