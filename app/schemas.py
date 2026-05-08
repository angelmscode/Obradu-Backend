#Creacion de contratos de datos

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models import RolUsuario, EstadoVehiculo, TipoAsistencia


# ESQUEMAS DE EMPRESA
class EmpresaBase(BaseModel):
    nombre: str

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaOut(EmpresaBase):
    id: int
    class Config:
        from_attributes = True

# ESQUEMAS USUARIOS
class UsuarioBase(BaseModel):
    nombre: str
    apellidos: str
    email: EmailStr
    rol: RolUsuario

class UsuarioCreate(UsuarioBase):
    password: str
    # El empresa_id no suele pedirse en el registro manual 
    # si el Jefe es quien crea al empleado
    empresa_id: Optional[int] = None 

class UsuarioOut(UsuarioBase):
    id: int
    empresa: Optional[EmpresaOut] = None
    empresa_id: int
    class Config:
        from_attributes = True

# ESQUEMA OBRAS
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

# ESQUEMAS LOGÍSTICA / MATERIALES
class MaterialBase(BaseModel):
    nombre: str
    stock_total: int = 0
    # No incluimos empresa_id aquí porque se asigna internamente

class MaterialOut(MaterialBase):
    id: int
    empresa_id: int
    class Config:
        from_attributes = True

class SumarStockRequest(BaseModel):
    cantidad: int

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

# ESQUEMAS RRHH / ASIGNACIONES
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

# ESQUEMAS VEHÍCULOS
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

class ReservaVehiculoCreate(BaseModel):
    vehiculo_id: int
    empleado_id: int
    fecha_reserva: date

class ReservaVehiculoOut(ReservaVehiculoCreate):
    id: int
    fecha_devolucion: Optional[date] = None
    class Config:
        from_attributes = True

# ESQUEMAS ASISTENCIAS / TAREAS
class AsistenciaTareaBase(BaseModel):
    obra_id: int
    tipo: TipoAsistencia
    descripcion: Optional[str] = None
    fecha: date

class AsistenciaTareaCreate(AsistenciaTareaBase):
    empleado_id: Optional[int] = None 

class AsistenciaTareaOut(AsistenciaTareaBase):
    id: int
    empleado_id: int
    hora_entrada: datetime
    hora_salida: Optional[datetime] = None
    completada: bool
    class Config:
        from_attributes = True

class AsignacionUpdate(BaseModel):
    empleado_id: int
    
class MaterialTareaOut(BaseModel):
    id: int
    material_nombre: Optional[str] = None
    cantidad: float

class AsistenciaTareaOut(AsistenciaTareaBase):
    id: int
    completada: Optional[bool] = None
    hora_entrada: Optional[datetime] = None
    hora_salida: Optional[datetime] = None
    materiales_consumidos: List[MaterialTareaOut] = []

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
    empresa_id: int

    class Config:
        from_attributes = True



class MaterialTareaCreate(BaseModel):
    material_id: int
    cantidad: float




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
    empresa_id: int
    usuario_id: Optional[int] = None
    nombre_usuario: Optional[str] = None

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


