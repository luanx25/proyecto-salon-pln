from database import SessionLocal
from models import Servicio, Empleado


def seed_datos():
    with SessionLocal() as db:
        if not db.query(Empleado).filter(Empleado.nombre == "Michell").first():
            db.add(Empleado(nombre="Michell", activo=True))

        if db.query(Servicio).count() == 0:
            servicios = [
                {"nombre": "manicura", "duracion_min": 30, "precio": 250.0},
                {"nombre": "pedicura", "duracion_min": 45, "precio": 300.0},
                {"nombre": "corte de cabello", "duracion_min": 30, "precio": 150.0},
                {"nombre": "tinte", "duracion_min": 90, "precio": 500.0},
                {"nombre": "peinado", "duracion_min": 45, "precio": 350.0},
            ]
            for s in servicios:
                db.add(Servicio(**s))

        db.commit()