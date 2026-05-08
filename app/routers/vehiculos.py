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


def obtener_usuario_seguro(db: Session, usuario_actual):
    if isinstance(usuario_actual, models.Usuario):
        return usuario_actual

    email_usuario = usuario_actual["email"] if isinstance(usuario_actual, dict) else usuario_actual
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email_usuario).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

# region CRUD Vehículos

@router.post("/", response_model=schemas.VehiculoOut)
def registrar_vehiculo(vehiculo: schemas.VehiculoBase, db: Session = Depends(get_db),
                       usuario_actual: str = Depends(get_usuario_actual)):
    # 1. Obtener jefe y empresa
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)

    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403,
                            detail="Acceso denegado: Solo los JEFES pueden registrar nuevos vehículos.")

    # 2. Comprobar que la matrícula no exista ya (a nivel global o de empresa)
    vehiculo_existente = db.query(models.Vehiculo).filter_by(matricula=vehiculo.matricula).first()
    if vehiculo_existente:
        raise HTTPException(status_code=400, detail="Ya existe un vehículo con esta matrícula")

    # 3. Crear vehículo asignando la empresa del jefe
    nuevo_vehiculo = models.Vehiculo(
        **vehiculo.model_dump(),
        empresa_id=jefe_logueado.empresa_id
    )
    db.add(nuevo_vehiculo)
    db.commit()
    db.refresh(nuevo_vehiculo)
    return nuevo_vehiculo


@router.get("/", response_model=List[schemas.VehiculoOut])
def obtener_vehiculos(db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    # FILTRO: Solo vehículos de su empresa
    vehiculos_db = db.query(models.Vehiculo).filter(
        models.Vehiculo.empresa_id == usuario_logueado.empresa_id
    ).all()

    resultado = []

    for v in vehiculos_db:
        vehiculo_dict = {
            "id": v.id,
            "matricula": v.matricula,
            "modelo": v.modelo,
            "estado": v.estado,
            "usuario_id": None,
            "nombre_usuario": None
        }

        if v.estado.name == "EN_USO":
            # Buscamos la reserva activa para este vehículo
            reserva = db.query(models.ReservaVehiculo).filter(
                models.ReservaVehiculo.vehiculo_id == v.id,
                models.ReservaVehiculo.fecha_devolucion == None
            ).first()

            if reserva:
                empleado = db.query(models.Usuario).filter(models.Usuario.id == reserva.empleado_id).first()
                if empleado:
                    vehiculo_dict["usuario_id"] = empleado.id
                    vehiculo_dict["nombre_usuario"] = f"{empleado.nombre} {empleado.apellidos}"

        resultado.append(vehiculo_dict)

    return resultado


# endregion

# region Reservas

@router.post("/reservar", response_model=schemas.ReservaVehiculoOut)
def reservar_vehiculo(reserva: schemas.ReservaVehiculoCreate, db: Session = Depends(get_db),
                      usuario_actual: str = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    # Comprobar que el vehículo existe Y es de la empresa
    vehiculo = db.query(models.Vehiculo).filter(
        models.Vehiculo.id == reserva.vehiculo_id,
        models.Vehiculo.empresa_id == usuario_logueado.empresa_id
    ).first()

    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado en tu flota")

    if vehiculo.estado.name != "DISPONIBLE":
        raise HTTPException(status_code=400, detail=f"El vehículo no está disponible ({vehiculo.estado.name})")

    # Comprobar que el empleado existe Y es de la misma empresa
    empleado = db.query(models.Usuario).filter(
        models.Usuario.id == reserva.empleado_id,
        models.Usuario.empresa_id == usuario_logueado.empresa_id
    ).first()

    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado en tu empresa")

    # Crear la reserva
    nueva_reserva = models.ReservaVehiculo(**reserva.model_dump())
    vehiculo.estado = models.EstadoVehiculo.EN_USO

    db.add(nueva_reserva)
    db.commit()
    db.refresh(nueva_reserva)

    return nueva_reserva


@router.put("/{vehiculo_id}/devolver")
def devolver_vehiculo(vehiculo_id: int, db: Session = Depends(get_db),
                      usuario_actual: str = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    # Validar propiedad del vehículo
    vehiculo = db.query(models.Vehiculo).filter(
        models.Vehiculo.id == vehiculo_id,
        models.Vehiculo.empresa_id == usuario_logueado.empresa_id
    ).first()

    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    if vehiculo.estado.name != "EN_USO":
        raise HTTPException(status_code=400, detail="El vehículo no está marcado como EN USO")

    reserva_activa = db.query(models.ReservaVehiculo).filter_by(
        vehiculo_id=vehiculo_id,
        fecha_devolucion=None
    ).first()

    if reserva_activa:
        reserva_activa.fecha_devolucion = date.today()

    vehiculo.estado = models.EstadoVehiculo.DISPONIBLE
    db.commit()

    return {"mensaje": f"Vehículo {vehiculo.matricula} devuelto correctamente."}


@router.put("/{vehiculo_id}/taller")
def enviar_a_taller(vehiculo_id: int, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)

    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Solo los JEFES pueden gestionar el taller.")

    vehiculo = db.query(models.Vehiculo).filter(
        models.Vehiculo.id == vehiculo_id,
        models.Vehiculo.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    vehiculo.estado = models.EstadoVehiculo.TALLER
    db.commit()

    return {"mensaje": f"Vehículo {vehiculo.matricula} enviado al TALLER."}


@router.put("/{vehiculo_id}/reparado")
def recuperar_de_taller(vehiculo_id: int, db: Session = Depends(get_db),
                        usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)

    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    vehiculo = db.query(models.Vehiculo).filter(
        models.Vehiculo.id == vehiculo_id,
        models.Vehiculo.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not vehiculo or vehiculo.estado.name != "TALLER":
        raise HTTPException(status_code=400, detail="El vehículo no está en el taller o no existe")

    vehiculo.estado = models.EstadoVehiculo.DISPONIBLE
    db.commit()

    return {"mensaje": f"Vehículo {vehiculo.matricula} reparado y DISPONIBLE."}
# endregion