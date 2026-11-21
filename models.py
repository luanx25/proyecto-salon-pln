from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Time, Table
from sqlalchemy.orm import relationship
from database import Base

empleado_servicio = Table(
    "empleado_servicio",
    Base.metadata,
    Column("empleado_id", ForeignKey("empleados.id"), primary_key=True),
    Column("servicio_id", ForeignKey("servicios.id"), primary_key=True),
)

class Empleado(Base):
    __tablename__ = "empleados"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True, nullable=False)
    activo = Column(Boolean, default=True)
    servicios = relationship("Servicio", secondary=empleado_servicio, back_populates="empleados")
    citas = relationship("Cita", back_populates="empleado")
    horarios = relationship(
        "HorarioEmpleado",
        back_populates="empleado",
        cascade="all, delete-orphan",
    )



class Servicio(Base):
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True, nullable=False)
    duracion_min = Column(Integer, default=30)
    precio = Column(Float, default=0.0)
    activo = Column(Boolean, default=True)
    empleados = relationship("Empleado", secondary=empleado_servicio, back_populates="servicios")
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

class HorarioEmpleado(Base):
    """Bloque de trabajo de un empleado en un día de la semana."""
    __tablename__ = "horarios_empleado"

    id = Column(Integer, primary_key=True, index=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=False)
    dia_semana = Column(Integer, nullable=False)  # 0=lunes ... 6=domingo
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)

    empleado = relationship("Empleado", back_populates="horarios")
