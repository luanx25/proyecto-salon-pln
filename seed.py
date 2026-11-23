from database import SessionLocal
from models import Servicio, Empleado, HorarioEmpleado, SeccionPagina
from datetime import time



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
        seed_horarios(db)
        seed_relacion_servicios(db)
        seed_relacion_servicios(db)
        seed_secciones(db)

def seed_horarios(db):
    michell = db.query(Empleado).filter(Empleado.nombre == "Michell").first()
    if michell and not michell.horarios:
        for dia in range(0, 6):  # lunes a sábado
            michell.horarios.append(
                HorarioEmpleado(dia_semana=dia, hora_inicio=time(10, 0), hora_fin=time(19, 0))
            )
        db.commit()

def seed_relacion_servicios(db):
    michell = db.query(Empleado).filter(Empleado.nombre == "Michell").first()
    if michell and not michell.servicios:
        michell.servicios = db.query(Servicio).all()
        db.commit()

SECCIONES_BASE = [
    dict(clave="inicio", tipo="hero", titulo="Realza tu belleza",
         subtitulo="Reserva tu cita en minutos, escribiendo lo que necesitas.",
         boton_texto="Reservar cita", boton_enlace="#reserva", orden=0),
    dict(clave="servicios", tipo="servicios", titulo="Nuestros servicios",
         subtitulo="Cuidado profesional para ti.", orden=1),
    dict(clave="nosotros", tipo="texto", titulo="Sobre nosotros",
         contenido="Somos un salón dedicado a que te sientas increíble.\nEdita este texto desde el panel de administración.",
         orden=2),
    dict(clave="equipo", tipo="equipo", titulo="Nuestro equipo", orden=3),
    dict(clave="reserva", tipo="reserva", titulo="Reserva tu cita",
         subtitulo="Escribe algo como: «Quiero una manicura mañana a las 4 pm».", orden=4),
    dict(clave="contacto", tipo="contacto", titulo="Contacto", orden=5),
]


def seed_secciones(db):
    if db.query(SeccionPagina).count() == 0:
        for s in SECCIONES_BASE:
            db.add(SeccionPagina(**s))
        db.commit()