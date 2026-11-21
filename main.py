from fastapi import FastAPI
from database import Base, engine, SessionLocal
from models import Servicio, Empleado
from routers import public, api

# Crea tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Salón de Belleza - Landing + PLN MVP",
    description="Prueba funcional: mensaje → PLN → validación de contacto → disponibilidad → guardado → interfaz"
)


def seed_datos():
    with SessionLocal() as db:
        # Seed de empleado
        michell = (
            db.query(Empleado)
            .filter(Empleado.nombre == "Michell")
            .first()
        )

        if not michell:
            db.add(Empleado(nombre="Michell", activo=True))

        # Seed de servicios
        if db.query(Servicio).count() == 0:
            servicios = [
                {"nombre": "manicura", "duracion_min": 30, "precio": 250.0},
                {"nombre": "pedicura", "duracion_min": 45, "precio": 300.0},
                {"nombre": "corte de cabello", "duracion_min": 30, "precio": 150.0},
                {"nombre": "tinte", "duracion_min": 90, "precio": 500.0},
                {"nombre": "peinado", "duracion_min": 45, "precio": 350.0},
            ]

            for servicio in servicios:
                db.add(Servicio(**servicio))

        db.commit()


seed_datos()

app.include_router(public.router)
app.include_router(api.router)

