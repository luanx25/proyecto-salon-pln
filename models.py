from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class Empleado(Base):
    __tablename__ = "empleados"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True, nullable=False)
    activo = Column(Boolean, default=True)

    citas = relationship("Cita", back_populates="empleado")


class Servicio(Base):
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True, nullable=False)
    duracion_min = Column(Integer, default=30)
    precio = Column(Float, default=0.0)
    activo = Column(Boolean, default=True)

    citas = relationship("Cita", back_populates="servicio")


class Cita(Base):
    __tablename__ = "citas"

    id = Column(Integer, primary_key=True, index=True)

    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=False)

    cliente_email = Column(String, nullable=False)
    cliente_telefono = Column(String, nullable=False)

    mensaje_original = Column(Text, nullable=True)

    fecha_hora = Column(DateTime, index=True, nullable=False)
    estado = Column(String, default="confirmada")
    origen = Column(String, default="landing")
    creado_en = Column(DateTime, default=datetime.now)

    servicio = relationship("Servicio", back_populates="citas")
    empleado = relationship("Empleado", back_populates="citas")