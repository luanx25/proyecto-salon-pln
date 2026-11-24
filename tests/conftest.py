from datetime import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import gcal
from database import Base
from models import Servicio, Empleado, HorarioEmpleado


@pytest.fixture(autouse=True)
def sin_google(monkeypatch):
    monkeypatch.setattr(gcal, "gcal_habilitado", lambda: False)


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