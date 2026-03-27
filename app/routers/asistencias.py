from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime
from app.database import SessionLocal
from app import models, schemas
from app.auth import get_usuario_actual

router = APIRouter(prefix="/asistencias", tags=["Fichajes y Tareas"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=schemas.AsistenciaTareaOut)
def registrar_fichaje_o_tarea(registro: schemas.AsistenciaTareaCreate, db: Session = Depends(get_db),
                              usuario_actual: str = Depends(get_usuario_actual)):
    usuario_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()

    if usuario_logueado.rol.value != "JEFE":
        registro.empleado_id = usuario_logueado.id

    # Comprobar que el empleado existe
    empleado = db.query(models.Usuario).filter_by(id=registro.empleado_id).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    # Comprobar que la obra existe
    obra = db.query(models.Obra).filter_by(id=registro.obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    # Comprobar si el empleado esta asignado a la obra o es un jefe
    if empleado.rol.value != "JEFE":
        asignacion = db.query(models.ObraEmpleado).filter_by(
            obra_id=registro.obra_id,
            empleado_id=registro.empleado_id
        ).first()
        if not asignacion:
            raise HTTPException(status_code=400, detail="Este empleado no está asignado a esta obra. Asígnelo primero.")
    # Crear el registro
    nuevo_registro = models.AsistenciaTarea(**registro.model_dump())
    db.add(nuevo_registro)
    db.commit()
    db.refresh(nuevo_registro)

    return nuevo_registro


@router.put("/{registro_id}/fichar_salida", response_model=schemas.AsistenciaTareaOut)
def fichar_salida(registro_id: int, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    usuario_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()

    # Buscar el registro
    registro = db.query(models.AsistenciaTarea).filter_by(id=registro_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    if usuario_logueado.rol.value != "JEFE" and registro.empleado_id != usuario_logueado.id:
        raise HTTPException(status_code=403, detail="Acceso denegado: No puedes fichar la salida de otro empleado.")

    # Validar que sea una ASISTENCIA y no una TAREA
    if registro.tipo.name != "ASISTENCIA":
        raise HTTPException(status_code=400, detail="Este botón es solo para fichar la salida de ASISTENCIAS.")

    # Validar que no haya fichado ya
    if registro.hora_salida:
        raise HTTPException(status_code=400, detail="Ya se ha registrado la salida para este turno.")

    # Sale a la hora actual
    registro.hora_salida = datetime.now()
    db.commit()
    db.refresh(registro)

    return registro


@router.put("/{tarea_id}/completar", response_model=schemas.AsistenciaTareaOut)
def completar_tarea(tarea_id: int, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    usuario_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()

    # Buscar la tarea
    tarea = db.query(models.AsistenciaTarea).filter_by(id=tarea_id).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    if usuario_logueado.rol.value != "JEFE" and tarea.empleado_id != usuario_logueado.id:
        raise HTTPException(status_code=403, detail="Acceso denegado: No puedes completar la tarea de otro empleado.")

    # Validar que sea una tarea
    if tarea.tipo.name != "TAREA":
        raise HTTPException(status_code=400, detail="Solo se pueden completar las TAREAS, no las ASISTENCIAS")

    # Marcar como completada
    tarea.completada = True
    db.commit()
    db.refresh(tarea)

    return tarea


@router.put("/{tarea_id}/deshacer")
def deshacer_tarea(tarea_id: int, db: Session = Depends(get_db)):
    tarea = db.query(models.AsistenciaTarea).filter(models.AsistenciaTarea.id == tarea_id).first()

    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    tarea.completada = False
    db.commit()

    return {"mensaje": "Tarea desmarcada con éxito"}

@router.get("/obra/{obra_id}", response_model=List[schemas.AsistenciaTareaOut])
def obtener_registros_obra(obra_id: int, db: Session = Depends(get_db),
                           usuario_actual: str = Depends(get_usuario_actual)):
    usuario_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()

    if usuario_logueado.rol.value == "JEFE":
        registros = db.query(models.AsistenciaTarea).filter_by(obra_id=obra_id).all()
    else:
        registros = db.query(models.AsistenciaTarea).filter_by(obra_id=obra_id, empleado_id=usuario_logueado.id).all()

    return registros