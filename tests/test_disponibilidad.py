from datetime import datetime, timedelta, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import Servicio, Empleado, HorarioEmpleado
from services import asignar_empleado_disponible, crear_cita, validar_disponibilidad


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    emp = Empleado(nombre="Michell", activo=True)
    for dia in range(7):
        emp.horarios.append(HorarioEmpleado(dia_semana=dia, hora_inicio=time(9, 0), hora_fin=time(19, 0)))

    tinte = Servicio(nombre="tinte", duracion_min=90, precio=500)
    manicura = Servicio(nombre="manicura", duracion_min=30, precio=250)
    emp.servicios = [tinte, manicura]

    session.add_all([emp, tinte, manicura])
    session.commit()
    yield session
    session.close()


def dia_futuro(hora, minuto=0):
    d = datetime.now() + timedelta(days=7)
    return d.replace(hour=hora, minute=minuto, second=0, microsecond=0)


def agendar(db, nombre_servicio, fecha_hora):
    servicio = db.query(Servicio).filter_by(nombre=nombre_servicio).first()
    empleado, _ = asignar_empleado_disponible(db, servicio, fecha_hora)
    return crear_cita(db, servicio, empleado, fecha_hora, "a@b.com", "5512345678", "test")


def test_rechaza_traslape(db):
    agendar(db, "tinte", dia_futuro(10, 0))  # ocupa 10:00-11:30
    manicura = db.query(Servicio).filter_by(nombre="manicura").first()

    empleado, _ = asignar_empleado_disponible(db, manicura, dia_futuro(10, 30))
    assert empleado is None


def test_acepta_cita_pegada(db):
    agendar(db, "tinte", dia_futuro(10, 0))
    manicura = db.query(Servicio).filter_by(nombre="manicura").first()

    empleado, _ = asignar_empleado_disponible(db, manicura, dia_futuro(11, 30))
    assert empleado is not None


def test_rechaza_si_no_cabe_antes_del_cierre(db):
    tinte = db.query(Servicio).filter_by(nombre="tinte").first()

    empleado, _ = asignar_empleado_disponible(db, tinte, dia_futuro(18, 0))
    assert empleado is None


def test_cita_cancelada_libera_horario(db):
    cita = agendar(db, "tinte", dia_futuro(10, 0))
    cita.estado = "cancelada"
    db.commit()

    tinte = db.query(Servicio).filter_by(nombre="tinte").first()
    empleado, _ = asignar_empleado_disponible(db, tinte, dia_futuro(10, 0))
    assert empleado is not None

def test_reprogramar_ignora_la_propia_cita(db):
    cita = agendar(db, "tinte", dia_futuro(10, 0))   # 10:00-11:30
    tinte = db.query(Servicio).filter_by(nombre="tinte").first()

    # Moverla 30 min choca consigo misma solo si no se excluye
    ok, _ = validar_disponibilidad(db, dia_futuro(10, 30), tinte, cita.empleado)
    assert not ok

    ok, _ = validar_disponibilidad(db, dia_futuro(10, 30), tinte, cita.empleado, excluir_cita_id=cita.id)
    assert ok

def test_bloqueo_externo_rechaza_el_horario(db, monkeypatch):
    import services
    monkeypatch.setattr(services, "hay_bloqueo_externo", lambda inicio, fin: True)

    manicura = db.query(Servicio).filter_by(nombre="manicura").first()
    empleado, mensaje = asignar_empleado_disponible(db, manicura, dia_futuro(12, 0))

    assert empleado is None
    assert "disponibilidad" in mensaje