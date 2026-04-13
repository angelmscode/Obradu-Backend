#Creacion de contratos de datos

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models import RolUsuario, EstadoVehiculo, TipoAsistencia

# ESQUEMAS USUARIOS
class UsuarioBase(BaseModel):
    nombre: str
    apellidos: str
    email: EmailStr
    rol: RolUsuario

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioOut(UsuarioBase):
    id: int
    class Config:
        from_attributes = True

# ESQUEMA OBRAS
class ObraBase(BaseModel):
    nombre: str
    direccion: str
    fecha_inicio: date
    fecha_fin: Optional[date] = None
    presupuesto: Optional[Decimal] = None
    jefe_id: int

class ObraOut(ObraBase):
    id: int
    progreso: float = 0.0

    class Config:
        from_attributes = True


# ESQUEMA ASIGNAR EMPLEADOS A OBRA
class ObraEmpleadoCreate(BaseModel):
    empleado_id: int
    fecha_asignacion: date

class ObraEmpleadoOut(BaseModel):
    id: int
    obra_id: int
    empleado_id: int
    fecha_asignacion: date

    class Config:
        from_attributes = True

# ESQUEMAS ASISTENCIAS Y TAREAS
class AsistenciaTareaBase(BaseModel):
    empleado_id: int
    obra_id: int
    tipo: TipoAsistencia
    descripcion: Optional[str] = None
    fecha: date

class AsistenciaTareaCreate(AsistenciaTareaBase):
    pass

class AsistenciaTareaOut(AsistenciaTareaBase):
    id: int
    completada: Optional[bool] = None
    hora_entrada: Optional[datetime] = None
    hora_salida: Optional[datetime] = None

    class Config:
        from_attributes = True

# ESQUEMAS MATERIALES
class MaterialBase(BaseModel):
    nombre: str
    stock_total: int = 0

class SumarStockRequest(BaseModel):
    cantidad: int

class MaterialOut(MaterialBase):
    id: int

    class Config:
        from_attributes = True

# ESQUEMAS PARA ASIGNAR MATERIAL A OBRA (LOGÍSTICA)
class MaterialObraCreate(BaseModel):
    material_id: int
    cantidad_asignada: int

class MaterialObraOut(BaseModel):
    id: int
    obra_id: int
    material_id: int
    cantidad_asignada: int

    class Config:
        from_attributes = True

class ObraMaterialListaOut(BaseModel):
    id: int
    material_nombre: str
    cantidad_asignada: int

    class Config:
        from_attributes = True

# ESQUEMAS VEHÍCULOS
class VehiculoBase(BaseModel):
    matricula: str
    modelo: str
    estado: EstadoVehiculo = EstadoVehiculo.DISPONIBLE

class VehiculoOut(VehiculoBase):
    id: int
    class Config:
        from_attributes = True

# ESQUEMAS RESERVAS VEHÍCULOS
class ReservaVehiculoCreate(BaseModel):
    vehiculo_id: int
    empleado_id: int
    fecha_reserva: date

class ReservaVehiculoOut(BaseModel):
    id: int
    vehiculo_id: int
    empleado_id: int
    fecha_reserva: date
    fecha_devolucion: Optional[date] = None

    class Config:
        from_attributes = True


