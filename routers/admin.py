from fastapi import APIRouter, Request
from fastapi.params import Depends
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from dependencies import get_admin_actual
from models import Usuario

router = APIRouter(prefix="/admin", dependencies=[Depends(get_admin_actual)])
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, admin: Usuario = Depends(get_admin_actual)):
    return templates.TemplateResponse(request, "admin/dashboard.html", {"admin": admin})
