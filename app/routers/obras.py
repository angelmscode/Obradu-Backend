# ENDPOINT OBRAS
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import SessionLocal
from app import models, schemas
from app.auth import get_usuario_actual

router = APIRouter(prefix="/obras", tags=["Obras"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# region Basicos
@router.post("/", response_model=schemas.ObraOut)
def crear_obra(obra: schemas.ObraBase, db: Session = Depends(get_db),
               usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()

    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden crear obras.")

    obra.jefe_id = jefe_logueado.id

    # Crear obra
    nueva_obra = models.Obra(**obra.model_dump())

    db.add(nueva_obra)
    db.commit()
    db.refresh(nueva_obra)

    return nueva_obra


@router.put("/{obra_id}", response_model=schemas.ObraOut)
def actualizar_obra(obra_id: int, obra_actualizada: schemas.ObraBase, db: Session = Depends(get_db),
                    usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden modificar obras.")

    # Buscar la obra a modificar
    obra = db.query(models.Obra).filter_by(id=obra_id).first()

    # Si no existe lanza error 404
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    # Si cambiamos al jefe se comprueba que el nuevo exista
    if obra_actualizada.jefe_id != obra.jefe_id:
        nuevo_jefe = db.query(models.Usuario).filter(models.Usuario.id == obra_actualizada.jefe_id).first()
        if not nuevo_jefe or nuevo_jefe.rol.value != "JEFE":
            raise HTTPException(status_code=400, detail="El nuevo jefe no existe o no tiene rol JEFE")

    # Actualizar todos los campos
    for clave, valor in obra_actualizada.model_dump().items():
        setattr(obra, clave, valor)

    # Guardar los cambios
    db.commit()
    db.refresh(obra)

    return obra


@router.delete("/{obra_id}")
def eliminar_obra(obra_id: int, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden borrar obras.")

    # Buscar obra por ID
    obra = db.query(models.Obra).filter_by(id=obra_id).first()

    # Si no existe salta error 404
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    # Si existe se borra
    db.delete(obra)
    db.commit()

    return {"mensaje": f"La obra con ID {obra_id} ha sido eliminada correctamente"}


@router.get("/", response_model=List[schemas.ObraOut])
def obtener_obras(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                  usuario_actual: str = Depends(get_usuario_actual)):
    usuario_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()

    if usuario_logueado.rol.value == "JEFE":
        # Si es jefe, ve todas las obras
        obras = db.query(models.Obra).offset(skip).limit(limit).all()
    else:
        # Si es empleado, solo ve las obras a las que está asignado
        obras = db.query(models.Obra).join(
            models.ObraEmpleado, models.Obra.id == models.ObraEmpleado.obra_id
        ).filter(
            models.ObraEmpleado.empleado_id == usuario_logueado.id
        ).offset(skip).limit(limit).all()

    # 🪄 MAGIA: Calculamos el progreso dinámico para cada obra
    for obra in obras:
        total_tareas = db.query(models.AsistenciaTarea).filter(
            models.AsistenciaTarea.obra_id == obra.id,
            models.AsistenciaTarea.tipo == "TAREA"
        ).count()

        tareas_completadas = db.query(models.AsistenciaTarea).filter(
            models.AsistenciaTarea.obra_id == obra.id,
            models.AsistenciaTarea.tipo == "TAREA",
            models.AsistenciaTarea.completada == True
        ).count()

        # Evitamos dividir por cero si la obra aún no tiene tareas
        if total_tareas > 0:
            obra.progreso = tareas_completadas / total_tareas
        else:
            obra.progreso = 0.0

    return obras
# endregion




# region Logistica

# ASIGNAR MATERIAL A UNA OBRA (LOGÍSTICA)
@router.post("/{obra_id}/materiales", response_model=schemas.MaterialObraOut)
def asignar_material_a_obra(obra_id: int, asignacion: schemas.MaterialObraCreate, db: Session = Depends(get_db),
                            usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden asignar material.")

    # Comprobar que la obra existe
    obra = db.query(models.Obra).filter_by(id=obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    # Comprobar que el material existe en el almacén
    material = db.query(models.Material).filter_by(id=asignacion.material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado en el inventario")

    # Comprobar si hay stock suficiente
    if material.stock_total < asignacion.cantidad_asignada:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente. Solo quedan {material.stock_total} unidades de {material.nombre}."
        )

    # Restar el stock del almacén general
    material.stock_total -= asignacion.cantidad_asignada

    # Tabla intermedia
    nueva_asignacion = models.MaterialObra(
        obra_id=obra_id,
        material_id=asignacion.material_id,
        cantidad_asignada=asignacion.cantidad_asignada
    )
    db.add(nueva_asignacion)

    # Guardar cambios
    db.commit()
    db.refresh(nueva_asignacion)

    return nueva_asignacion


# VER MATERIALES ASIGNADOS A UNA OBRA
@router.get("/{obra_id}/materiales")
def obtener_materiales_de_obra(obra_id: int, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    obra = db.query(models.Obra).filter_by(id=obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    resultados = db.query(models.MaterialObra, models.Material).join(
        models.Material, models.MaterialObra.material_id == models.Material.id
    ).filter(
        models.MaterialObra.obra_id == obra_id
    ).all()

    lista_materiales = []
    for asignacion, material in resultados:
        lista_materiales.append({
            "id": material.id,
            "nombre": material.nombre,
            "cantidad_asignada": asignacion.cantidad_asignada
        })

    return lista_materiales

# endregion

# region RRHH

# ASIGNAR EMPLEADO A UNA OBRA
@router.post("/{obra_id}/empleados", response_model=schemas.ObraEmpleadoOut)
def asignar_empleado_a_obra(obra_id: int, asignacion: schemas.ObraEmpleadoCreate, db: Session = Depends(get_db),
                            usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden asignar empleados.")

    # Comprobar que la obra existe
    obra = db.query(models.Obra).filter_by(id=obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    # Comprobar que el empleado existe
    empleado = db.query(models.Usuario).filter_by(id=asignacion.empleado_id).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    # Comprobar que no esté ya asignado a esta obra
    asignacion_previa = db.query(models.ObraEmpleado).filter_by(
        obra_id=obra_id,
        empleado_id=asignacion.empleado_id
    ).first()
    if asignacion_previa:
        raise HTTPException(status_code=400, detail="Este empleado ya está trabajando en esta obra")

    # Crear el registro
    nueva_asignacion = models.ObraEmpleado(
        obra_id=obra_id,
        empleado_id=asignacion.empleado_id,
        fecha_asignacion=asignacion.fecha_asignacion
    )
    db.add(nueva_asignacion)
    db.commit()
    db.refresh(nueva_asignacion)

    return nueva_asignacion


# VER EMPLEADOS DE UNA OBRA
@router.get("/{obra_id}/empleados", response_model=List[schemas.UsuarioOut])
def obtener_empleados_de_obra(obra_id: int, db: Session = Depends(get_db),usuario_actual: str = Depends(get_usuario_actual)):
    # Comprobar que la obra existe
    obra = db.query(models.Obra).filter_by(id=obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    # Unir tablas y encontrar
    empleados = db.query(models.Usuario).join(
        models.ObraEmpleado, models.Usuario.id == models.ObraEmpleado.empleado_id
    ).filter(
        models.ObraEmpleado.obra_id == obra_id
    ).all()

    return empleados


# PANEL JEFE: ESTADÍSTICAS GENERALES
@router.get("/estadisticas/panel-jefe")
def obtener_estadisticas_panel(db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo para JEFES.")

    hoy = date.today()
    obras_activas = db.query(models.Obra).filter(
        (models.Obra.fecha_fin == None) | (models.Obra.fecha_fin >= hoy)
    ).count()

    personal_total = db.query(models.Usuario).filter(models.Usuario.rol == "EMPLEADO").count()

    vehiculos_uso = db.query(models.Vehiculo).filter(models.Vehiculo.estado == "EN_USO").count()

    ultimas_obras = db.query(models.Obra).order_by(models.Obra.id.desc()).limit(3).all()
    progreso_obras = []
    for obra in ultimas_obras:
        total_tareas = db.query(models.AsistenciaTarea).filter(
            models.AsistenciaTarea.obra_id == obra.id,
            models.AsistenciaTarea.tipo == "TAREA"
        ).count()

        tareas_completadas = db.query(models.AsistenciaTarea).filter(
            models.AsistenciaTarea.obra_id == obra.id,
            models.AsistenciaTarea.tipo == "TAREA",
            models.AsistenciaTarea.completada == True
        ).count()

        # Evitar división por cero
        porcentaje = 0.0
        if total_tareas > 0:
            porcentaje = tareas_completadas / total_tareas

        progreso_obras.append({
            "nombre": obra.nombre,
            "progreso": porcentaje
        })

    vehiculos_disponibles = db.query(models.Vehiculo).filter(models.Vehiculo.estado == "DISPONIBLE").count()
    vehiculos_taller = db.query(models.Vehiculo).filter(models.Vehiculo.estado == "TALLER").count()

    personal_ocupado = db.query(models.ObraEmpleado).distinct(models.ObraEmpleado.empleado_id).count()

    obras_finalizadas = db.query(models.Obra).filter(
        models.Obra.fecha_fin != None,
        models.Obra.fecha_fin < hoy
    ).count()

    return {
        "obras_activas": obras_activas,
        "obras_finalizadas": obras_finalizadas,
        "personal_total": personal_total,
        "personal_ocupado": personal_ocupado,
        "vehiculos_uso": vehiculos_uso,
        "vehiculos_disponibles": vehiculos_disponibles,
        "vehiculos_taller": vehiculos_taller,
        "progreso_obras": progreso_obras
    }
# endregion