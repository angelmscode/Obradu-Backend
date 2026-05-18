# Creación de contratos de datos
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models import RolUsuario, EstadoVehiculo, TipoAsistencia


# EMPRESA
class EmpresaBase(BaseModel):
    nombre: str

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaOut(EmpresaBase):
    id: int
    class Config:
        from_attributes = True


# USUARIOS
class RegistroJefeConEmpresa(BaseModel):
    nombre_empresa: str
    nombre: str
    apellidos: str
    email: EmailStr
    password: str

class UsuarioBase(BaseModel):
    nombre: str
    apellidos: str
    email: EmailStr
    rol: RolUsuario

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioOut(UsuarioBase):
    id: int
    empresa_id: int
    empresa: Optional[EmpresaOut] = None
    class Config:
        from_attributes = True


# OBRAS
class ObraBase(BaseModel):
    nombre: str
    direccion: str
    fecha_inicio: date
    fecha_fin: Optional[date] = None
    presupuesto: Optional[Decimal] = None

class ObraCreate(ObraBase):
    pass

class ObraOut(ObraBase):
    id: int
    jefe_id: int
    empresa_id: int
    progreso: float = 0.0
    class Config:
        from_attributes = True


# MATERIALES (inventario global)
class MaterialBase(BaseModel):
    nombre: str
    stock_total: int = 0

class MaterialOut(MaterialBase):
    id: int
    empresa_id: int
    class Config:
        from_attributes = True

class SumarStockRequest(BaseModel):
    cantidad: int


# MATERIALES EN OBRA (logística)
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


# VEHÍCULOS

class VehiculoBase(BaseModel):
    matricula: str
    modelo: str
    estado: EstadoVehiculo = EstadoVehiculo.DISPONIBLE

class VehiculoOut(VehiculoBase):
    id: int
    empresa_id: int
    usuario_id: Optional[int] = None
    nombre_usuario: Optional[str] = None
    class Config:
        from_attributes = True


# RESERVAS DE VEHÍCULOS

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


# ASIGNACIONES OBRA-EMPLEADO

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


# ASISTENCIAS Y TAREAS
class AsistenciaTareaBase(BaseModel):
    obra_id: int
    tipo: TipoAsistencia
    descripcion: Optional[str] = None
    fecha: date

class AsistenciaTareaCreate(AsistenciaTareaBase):
    empleado_id: Optional[int] = None

class MaterialTareaCreate(BaseModel):
    material_id: int
    cantidad: float

class MaterialTareaOut(BaseModel):
    id: int
    material_nombre: Optional[str] = None
    cantidad: float
    class Config:
        from_attributes = True

# Versión con materiales consumidos
class AsistenciaTareaOut(AsistenciaTareaBase):
    id: int
    empleado_id: int
    completada: Optional[bool] = None
    hora_entrada: Optional[datetime] = None
    hora_salida: Optional[datetime] = None
    materiales_consumidos: List[MaterialTareaOut] = []
    class Config:
        from_attributes = True

class AsignacionUpdate(BaseModel):
    empleado_id: int