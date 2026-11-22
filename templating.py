from fastapi import Request
from fastapi.templating import Jinja2Templates

from constantes import ESTADOS_CITA

templates = Jinja2Templates(directory="templates")


def flash(request: Request, mensaje: str, tipo: str = "ok"):
    """Guarda un mensaje (ok | warn | error) para mostrarlo en la siguiente página."""
    request.session.setdefault("_flashes", []).append({"msg": mensaje, "tipo": tipo})


def _leer_flashes(request: Request):
    return request.session.pop("_flashes", [])


templates.env.globals["get_flashes"] = _leer_flashes
templates.env.globals["ESTADOS"] = ESTADOS_CITA
templates.env.filters["fecha"] = lambda d: d.strftime("%d/%m/%Y %H:%M") if d else ""
templates.env.filters["moneda"] = lambda v: f"${v:,.2f}"


def render_admin(request, plantilla, admin, seccion, status_code=200, **contexto):
    return templates.TemplateResponse(
        request,
        plantilla,
        {"admin": admin, "seccion": seccion, **contexto},
        status_code=status_code,
    )