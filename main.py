from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from config import SECRET_KEY
from database import Base, engine
from routers import public, api, auth, admin, admin_servicios, admin_empleados
from seed import seed_datos
from fastapi.responses import RedirectResponse
from dependencies import RedirigirALogin
from fastapi.staticfiles import StaticFiles

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Salón de Belleza - Landing + PLN MVP",
    description="Prueba funcional: mensaje → PLN → validación de contacto → disponibilidad → guardado → interfaz"
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=60 * 60 * 8,   # la sesión dura 8 horas
    same_site="lax",
    https_only=False,      # cámbialo a True al desplegar con HTTPS
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(public.router)
app.include_router(api.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(admin_servicios.router)
app.include_router(admin_empleados.router)

@app.exception_handler(RedirigirALogin)
async def redirigir_a_login(request, exc):
    return RedirectResponse("/admin/login", status_code=303)




seed_datos()