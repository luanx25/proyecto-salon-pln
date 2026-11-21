from fastapi import FastAPI
from database import Base, engine
from routers import public, api
from seed import seed_datos

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Salón de Belleza - Landing + PLN MVP",
    description="Prueba funcional: mensaje → PLN → validación de contacto → disponibilidad → guardado → interfaz"
)

app.include_router(public.router)
app.include_router(api.router)

seed_datos()