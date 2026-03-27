from sqlalchemy import Column, Integer, String, ForeignKey, Date, Boolean, Enum, DateTime, Numeric
from app.database import Base
from datetime import datetime

import enum


# Enums
class RolUsuario(enum.Enum):
    JEFE = "JEFE"
    EMPLEADO = "EMPLEADO"

class EstadoVehiculo(enum.Enum):
    DISPONIBLE = "DISPONIBLE"
    EN_USO = "EN_USO"
    TALLER = "TALLER"

class TipoAsistencia(enum.Enum):
    ASISTENCIA = "ASISTENCIA"
    TAREA = "TAREA"

class TipoUnidad(str, enum.Enum):
    METROS = "metros"
    KG = "kg"
    UDS = "uds"
    SACOS = "sacos"

# Tablas Principales
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(RolUsuario), nullable=False)

class Vehiculo(Base):
    __tablename__ = "vehiculos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    matricula = Column(String(20), unique=True, nullable=False)
    modelo = Column(String(100), nullable=False)
    estado = Column(Enum(EstadoVehiculo), server_default="DISPONIBLE")

class Material(Base):
    __tablename__ = "materiales"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(150), nullable=False)
    stock_total = Column(Integer, server_default="0")

class Obra(Base):
    __tablename__ = "obras"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(150), nullable=False)
    direccion = Column(String(255), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=True)
    presupuesto = Column(Numeric(10, 2), nullable=True)
    jefe_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)

# Tablas intermedias
class ObraEmpleado(Base):
    __tablename__ = "obras_empleados"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    obra_id = Column(Integer, ForeignKey("obras.id", ondelete="CASCADE"), nullable=False)
    empleado_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    fecha_asignacion = Column(Date, nullable=False)

class MaterialObra(Base):
    __tablename__ = "materiales_obra"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    obra_id = Column(Integer, ForeignKey("obras.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(Integer, ForeignKey("materiales.id", ondelete="CASCADE"), nullable=False)
    cantidad_asignada = Column(Integer, nullable=False)

class ReservaVehiculo(Base):
    __tablename__ = "reservas_vehiculos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id", ondelete="CASCADE"), nullable=False)
    empleado_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    fecha_reserva = Column(Date, nullable=False)
    fecha_devolucion = Column(Date, nullable=True)

class AsistenciaTarea(Base):
    __tablename__ = "asistencias_tareas"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    empleado_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    obra_id = Column(Integer, ForeignKey("obras.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(Enum(TipoAsistencia), nullable=False)
    descripcion = Column(String(255), nullable=True)
    fecha = Column(Date, nullable=False)
    hora_entrada = Column(DateTime, default= datetime.now)
    hora_salida = Column(DateTime, nullable=True)
    completada = Column(Boolean, server_default="0")