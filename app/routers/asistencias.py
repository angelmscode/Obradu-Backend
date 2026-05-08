from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime
from app.database import SessionLocal
from app import models, schemas
from app.auth import get_usuario_actual, obtener_usuario_seguro
from app.schemas import AsignacionUpdate

router = APIRouter(prefix="/asistencias", tags=["Fichajes y Tareas"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=schemas.AsistenciaTareaOut)
def registrar_fichaje_o_tarea(registro: schemas.AsistenciaTareaCreate, db: Session = Depends(get_db),
                              usuario_actual: dict = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    if usuario_logueado.rol.value != "JEFE":
        registro.empleado_id = usuario_logueado.id

    # Comprobar que el empleado existe Y pertenece a la misma empresa
    empleado = db.query(models.Usuario).filter(
        models.Usuario.id == registro.empleado_id,
        models.Usuario.empresa_id == usuario_logueado.empresa_id
    ).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado o no pertenece a tu empresa")

    # Comprobar que la obra existe Y pertenece a la misma empresa
    obra = db.query(models.Obra).filter(
        models.Obra.id == registro.obra_id,
        models.Obra.empresa_id == usuario_logueado.empresa_id
    ).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada o no pertenece a tu empresa")

    # Comprobar si el empleado esta asignado a la obra o es un jefe
    if empleado.rol.value != "JEFE":
        asignacion = db.query(models.ObraEmpleado).filter_by(
            obra_id=registro.obra_id,
            empleado_id=registro.empleado_id
        ).first()
        if not asignacion:
            raise HTTPException(status_code=400, detail="Este empleado no está asignado a esta obra. Asígnelo primero.")

    if registro.tipo == "ASISTENCIA":
        jornada_pendiente = db.query(models.AsistenciaTarea).filter(
            models.AsistenciaTarea.empleado_id == registro.empleado_id,
            models.AsistenciaTarea.tipo == "ASISTENCIA",
            models.AsistenciaTarea.hora_salida == None
        ).first()

        if jornada_pendiente:
            raise HTTPException(
                status_code=400,
                detail=f"Este empleado no ha terminado su jornada anterior (ID: {jornada_pendiente.id})."
            )

    nuevo_registro = models.AsistenciaTarea(**registro.model_dump())
    db.add(nuevo_registro)
    db.commit()
    db.refresh(nuevo_registro)

    return nuevo_registro


@router.post("/{tarea_id}/materiales", response_model=schemas.MaterialTareaOut)
def registrar_material_tarea(tarea_id: int, registro: schemas.MaterialTareaCreate,
                             db: Session = Depends(get_db),
                             usuario_actual: dict = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    tarea = db.query(models.AsistenciaTarea).join(models.Obra).filter(
        models.AsistenciaTarea.id == tarea_id,
        models.Obra.empresa_id == usuario_logueado.empresa_id
    ).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o sin permisos")

    # Verificar que el material pertenece a la misma empresa
    material = db.query(models.Material).filter(
        models.Material.id == registro.material_id,
        models.Material.empresa_id == usuario_logueado.empresa_id
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail="El material no existe en el inventario de la empresa")

    nuevo_consumo = models.MaterialTarea(
        tarea_id=tarea_id,
        material_id=registro.material_id,
        cantidad=registro.cantidad
    )

    material.stock_total -= registro.cantidad
    db.add(nuevo_consumo)
    db.commit()
    db.refresh(nuevo_consumo)
    return nuevo_consumo


@router.put("/{registro_id}/fichar_salida", response_model=schemas.AsistenciaTareaOut)
def fichar_salida(registro_id: int, db: Session = Depends(get_db), usuario_actual: dict = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    # Buscar el registro asegurando la pertenencia a la empresa
    registro = db.query(models.AsistenciaTarea).join(models.Obra).filter(
        models.AsistenciaTarea.id == registro_id,
        models.Obra.empresa_id == usuario_logueado.empresa_id
    ).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado o sin permisos")

    if usuario_logueado.rol.value != "JEFE" and registro.empleado_id != usuario_logueado.id:
        raise HTTPException(status_code=403, detail="Acceso denegado: No puedes fichar la salida de otro empleado.")

    if registro.tipo.name != "ASISTENCIA":
        raise HTTPException(status_code=400, detail="Este botón es solo para fichar la salida de ASISTENCIAS.")

    if registro.hora_salida:
        raise HTTPException(status_code=400, detail="Ya se ha registrado la salida para este turno.")

    registro.hora_salida = datetime.now()
    db.commit()
    db.refresh(registro)

    return registro


@router.put("/{tarea_id}/completar", response_model=schemas.AsistenciaTareaOut)
def completar_tarea(tarea_id: int, db: Session = Depends(get_db), usuario_actual: dict = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    tarea = db.query(models.AsistenciaTarea).join(models.Obra).filter(
        models.AsistenciaTarea.id == tarea_id,
        models.Obra.empresa_id == usuario_logueado.empresa_id
    ).first()

    if not tarea:
        raise HTTPException(status_code=404, detail="Registro no encontrado o sin permisos")

    if usuario_logueado.rol.value != "JEFE" and tarea.empleado_id != usuario_logueado.id:
        raise HTTPException(status_code=403, detail="Acceso denegado: No puedes completar la tarea de otro empleado.")

    if tarea.tipo.name != "TAREA":
        raise HTTPException(status_code=400, detail="Solo se pueden completar las TAREAS, no las ASISTENCIAS")

    tarea.completada = True
    db.commit()
    db.refresh(tarea)

    return tarea


@router.put("/{tarea_id}/deshacer")
def deshacer_tarea(tarea_id: int, db: Session = Depends(get_db), usuario_actual: dict = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    tarea = db.query(models.AsistenciaTarea).join(models.Obra).filter(
        models.AsistenciaTarea.id == tarea_id,
        models.Obra.empresa_id == usuario_logueado.empresa_id
    ).first()

    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o sin permisos")

    tarea.completada = False
    db.commit()

    return {"mensaje": "Tarea desmarcada con éxito"}


@router.get("/obra/{obra_id}", response_model=List[schemas.AsistenciaTareaOut])
def obtener_registros_obra(obra_id: int, db: Session = Depends(get_db),
                           usuario_actual: dict = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    obra = db.query(models.Obra).filter(
        models.Obra.id == obra_id,
        models.Obra.empresa_id == usuario_logueado.empresa_id
    ).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada o no pertenece a tu empresa")

    if usuario_logueado.rol.value == "JEFE":
        registros = db.query(models.AsistenciaTarea).filter_by(obra_id=obra_id).all()
    else:
        registros = db.query(models.AsistenciaTarea).filter_by(obra_id=obra_id, empleado_id=usuario_logueado.id).all()

    return registros


@router.put("/{tarea_id}/asignar", response_model=schemas.AsistenciaTareaOut)
def reasignar_tarea(tarea_id: int, datos: AsignacionUpdate, db: Session = Depends(get_db),
                    usuario_actual: dict = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    if usuario_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los jefes pueden reasignar tareas.")

    tarea = db.query(models.AsistenciaTarea).join(models.Obra).filter(
        models.AsistenciaTarea.id == tarea_id,
        models.Obra.empresa_id == usuario_logueado.empresa_id
    ).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o sin permisos")

    if tarea.tipo.name != "TAREA":
        raise HTTPException(status_code=400, detail="Solo se pueden reasignar TAREAS, no ASISTENCIAS.")

    # Asegurar que el nuevo empleado pertenece a la misma empresa
    nuevo_empleado = db.query(models.Usuario).filter(
        models.Usuario.id == datos.empleado_id,
        models.Usuario.empresa_id == usuario_logueado.empresa_id
    ).first()
    if not nuevo_empleado:
        raise HTTPException(status_code=404, detail="El empleado seleccionado no existe o no es de tu empresa.")

    tarea.empleado_id = datos.empleado_id
    db.commit()
    db.refresh(tarea)

    return tarea