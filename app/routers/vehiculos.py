from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import SessionLocal
from app import models, schemas
from datetime import date
from app.auth import get_usuario_actual

router = APIRouter(prefix="/vehiculos", tags=["Vehículos"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# region CRUD Vehículos

@router.post("/", response_model=schemas.VehiculoOut)
def registrar_vehiculo(vehiculo: schemas.VehiculoBase, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden registrar nuevos vehículos.")

    # Comprobar que la matrícula no exista ya
    vehiculo_existente = db.query(models.Vehiculo).filter_by(matricula=vehiculo.matricula).first()
    if vehiculo_existente:
        raise HTTPException(status_code=400, detail="Ya existe un vehículo con esta matrícula")

    nuevo_vehiculo = models.Vehiculo(**vehiculo.model_dump())
    db.add(nuevo_vehiculo)
    db.commit()
    db.refresh(nuevo_vehiculo)
    return nuevo_vehiculo


@router.get("/", response_model=List[schemas.VehiculoOut])
def obtener_vehiculos(db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    return db.query(models.Vehiculo).all()


# endregion

# region Reservas

@router.post("/reservar", response_model=schemas.ReservaVehiculoOut)
def reservar_vehiculo(reserva: schemas.ReservaVehiculoCreate, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    # Comprobar que el vehículo existe
    vehiculo = db.query(models.Vehiculo).filter_by(id=reserva.vehiculo_id).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    # Comprobar que está disponible
    if vehiculo.estado.name != "DISPONIBLE":
        raise HTTPException(status_code=400,
                            detail=f"El vehículo no está disponible. Estado actual: {vehiculo.estado.name}")

    # Comprobar que el empleado existe
    empleado = db.query(models.Usuario).filter_by(id=reserva.empleado_id).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    # Crear la reserva
    nueva_reserva = models.ReservaVehiculo(**reserva.model_dump())

    # Cambiar el estado del vehículo a EN_USO
    vehiculo.estado = models.EstadoVehiculo.EN_USO

    db.add(nueva_reserva)
    db.commit()
    db.refresh(nueva_reserva)

    return nueva_reserva


# DEVOLVER UN VEHÍCULO
@router.put("/{vehiculo_id}/devolver")
def devolver_vehiculo(vehiculo_id: int, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    # Buscar el vehículo
    vehiculo = db.query(models.Vehiculo).filter_by(id=vehiculo_id).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    # Comprobar que está en uso
    if vehiculo.estado.name != "EN_USO":
        raise HTTPException(status_code=400, detail="El vehículo no está en uso actualmente")

    # Buscar la reserva activa
    reserva_activa = db.query(models.ReservaVehiculo).filter_by(
        vehiculo_id=vehiculo_id,
        fecha_devolucion=None
    ).first()

    # Cerrar la reserva y liberar el vehículo
    if reserva_activa:
        reserva_activa.fecha_devolucion = date.today()  # Le pone la fecha de hoy

    vehiculo.estado = models.EstadoVehiculo.DISPONIBLE

    db.commit()

    return {"mensaje": f"Vehículo {vehiculo.matricula} devuelto y DISPONIBLE."}


# ENVIAR AL TALLER
@router.put("/{vehiculo_id}/taller")
def enviar_a_taller(vehiculo_id: int, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden mandar vehículos al taller.")

    # Buscar el vehículo
    vehiculo = db.query(models.Vehiculo).filter_by(id=vehiculo_id).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    # Cambiar el estado
    vehiculo.estado = models.EstadoVehiculo.TALLER

    db.commit()

    return {"mensaje": f"Vehículo {vehiculo.matricula} enviado al TALLER."}


# RECUPERAR VEHÍCULO DEL TALLER (REPARADO)
@router.put("/{vehiculo_id}/reparado")
def recuperar_de_taller(vehiculo_id: int, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden autorizar la salida del taller.")

    # Buscar el vehículo
    vehiculo = db.query(models.Vehiculo).filter_by(id=vehiculo_id).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    # Comprobar que realmente está en el taller
    if vehiculo.estado.name != "TALLER":
        raise HTTPException(status_code=400, detail="El vehículo no está en el taller actualmente")

    # Ponerlo de vuelta a disponible
    vehiculo.estado = models.EstadoVehiculo.DISPONIBLE

    db.commit()

    return {"mensaje": f"Vehículo {vehiculo.matricula} reparado y de vuelta a la flota (DISPONIBLE)."}

# endregion