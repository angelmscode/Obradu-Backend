# ENDPOINT OBRAS
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import SessionLocal
from app import models, schemas
from app.auth import get_usuario_actual, obtener_usuario_seguro

router = APIRouter(prefix="/obras", tags=["Obras"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# region Basicos
@router.post("/", response_model=schemas.ObraOut)
def crear_obra(obra: schemas.ObraCreate, db: Session = Depends(get_db),
               usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)

    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden crear obras.")

    nueva_obra = models.Obra(
        **obra.model_dump(),
        jefe_id=jefe_logueado.id,
        empresa_id=jefe_logueado.empresa_id
    )

    db.add(nueva_obra)
    db.commit()
    db.refresh(nueva_obra)

    return nueva_obra


@router.put("/{obra_id}", response_model=schemas.ObraOut)
def actualizar_obra(obra_id: int, obra_actualizada: schemas.ObraBase, db: Session = Depends(get_db),
                    usuario_actual: str = Depends(get_usuario_actual)):
    # 1. Usamos la función segura para obtener al usuario y su empresa
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)

    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden modificar obras.")

    obra = db.query(models.Obra).filter(
        models.Obra.id == obra_id,
        models.Obra.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada o no tienes permisos")

    if obra_actualizada.jefe_id != obra.jefe_id:
        nuevo_jefe = db.query(models.Usuario).filter(
            models.Usuario.id == obra_actualizada.jefe_id,
            models.Usuario.rol == "JEFE",
            models.Usuario.empresa_id == jefe_logueado.empresa_id
        ).first()

        if not nuevo_jefe:
            raise HTTPException(status_code=400, detail="El nuevo jefe no es válido o pertenece a otra empresa")

    for clave, valor in obra_actualizada.model_dump().items():
        setattr(obra, clave, valor)

    db.commit()
    db.refresh(obra)
    return obra


@router.delete("/{obra_id}")
def eliminar_obra(obra_id: int, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)

    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden borrar obras.")

    obra = db.query(models.Obra).filter(
        models.Obra.id == obra_id,
        models.Obra.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada o no tienes permiso")

    db.delete(obra)
    db.commit()

    return {"mensaje": f"La obra con ID {obra_id} ha sido eliminada correctamente"}


@router.get("/", response_model=List[schemas.ObraOut])
def obtener_obras(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                  usuario_actual: str = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    if usuario_logueado.rol.value == "JEFE":
        # El jefe solo ve las obras de su empresa
        obras = db.query(models.Obra).filter(
            models.Obra.empresa_id == usuario_logueado.empresa_id
        ).offset(skip).limit(limit).all()
    else:
        # El empleado solo ve las obras a las que está asignado
        obras = db.query(models.Obra).join(
            models.ObraEmpleado, models.Obra.id == models.ObraEmpleado.obra_id
        ).filter(
            models.ObraEmpleado.empleado_id == usuario_logueado.id,
            models.Obra.empresa_id == usuario_logueado.empresa_id
        ).offset(skip).limit(limit).all()

    # Cálculo del progreso
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

        obra.progreso = (tareas_completadas / total_tareas) if total_tareas > 0 else 0.0

    return obras
# endregion


# region Logistica

# ASIGNAR MATERIAL A UNA OBRA
@router.post("/{obra_id}/materiales", response_model=schemas.MaterialObraOut)
def asignar_material_a_obra(obra_id: int, asignacion: schemas.MaterialObraCreate, db: Session = Depends(get_db),
                            usuario_actual: str = Depends(get_usuario_actual)):
    # Usuario seguro
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)

    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden asignar material.")

    # Comprobar que la obra existe Y pertenece a su empresa
    obra = db.query(models.Obra).filter(
        models.Obra.id == obra_id,
        models.Obra.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada o no tienes acceso")

    # Comprobar que el material existe en el almacén de su empresa
    material = db.query(models.Material).filter(
        models.Material.id == asignacion.material_id,
        models.Material.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado en tu inventario")

    # Comprobar stock
    if material.stock_total < asignacion.cantidad_asignada:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente en tu almacén. Solo quedan {material.stock_total} unidades."
        )

    # Restar el stock del almacén general
    material.stock_total -= asignacion.cantidad_asignada

    # Buscar si ya había ese material en esa obra
    asignacion_existente = db.query(models.MaterialObra).filter(
        models.MaterialObra.obra_id == obra_id,
        models.MaterialObra.material_id == asignacion.material_id
    ).first()

    if asignacion_existente:
        asignacion_existente.cantidad_asignada += asignacion.cantidad_asignada
        db.commit()
        db.refresh(asignacion_existente)
        return asignacion_existente
    else:
        nueva_asignacion = models.MaterialObra(
            obra_id=obra_id,
            material_id=asignacion.material_id,
            cantidad_asignada=asignacion.cantidad_asignada
        )
        db.add(nueva_asignacion)
        db.commit()
        db.refresh(nueva_asignacion)
        return nueva_asignacion


# VER MATERIALES ASIGNADOS A UNA OBRA
@router.get("/{obra_id}/materiales")
def obtener_materiales_de_obra(obra_id: int, db: Session = Depends(get_db),
                               usuario_actual: str = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    obra = db.query(models.Obra).filter(
        models.Obra.id == obra_id,
        models.Obra.empresa_id == usuario_logueado.empresa_id
    ).first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada o no tienes acceso")

    resultados = db.query(models.MaterialObra, models.Material).join(
        models.Material, models.MaterialObra.material_id == models.Material.id
    ).filter(
        models.MaterialObra.obra_id == obra_id,
        models.Material.empresa_id == usuario_logueado.empresa_id
    ).all()

    lista_materiales = []
    for asignacion, material in resultados:
        lista_materiales.append({
            "id": material.id,
            "nombre": material.nombre,
            "cantidad_asignada": asignacion.cantidad_asignada
        })

    return lista_materiales


@router.put("/{obra_id}/materiales/{material_id}/consumir")
def consumir_material_obra(
        obra_id: int,
        material_id: int,
        datos: schemas.SumarStockRequest,
        db: Session = Depends(get_db),
        usuario_actual: str = Depends(get_usuario_actual)
):
    # Obtener usuario y empresa
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    # Verificar que la obra pertenece a su empresa
    obra = db.query(models.Obra).filter(
        models.Obra.id == obra_id,
        models.Obra.empresa_id == usuario_logueado.empresa_id
    ).first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada o no tienes acceso.")

    # Buscar la asignación de ese material en esa obra
    mat_obra = db.query(models.MaterialObra).filter(
        models.MaterialObra.obra_id == obra_id,
        models.MaterialObra.material_id == material_id
    ).first()

    if not mat_obra:
        raise HTTPException(status_code=404, detail="Este material no está asignado a esta obra.")

    # Validar cantidad
    if mat_obra.cantidad_asignada < datos.cantidad:
        raise HTTPException(status_code=400,
                            detail=f"No hay suficiente stock en la obra. Quedan {mat_obra.cantidad_asignada} uds.")

    # Actualizar (consumir)
    mat_obra.cantidad_asignada -= datos.cantidad
    db.commit()

    return {
        "mensaje": "Material consumido correctamente",
        "restante_en_obra": mat_obra.cantidad_asignada
    }


@router.put("/{obra_id}/materiales/{material_id}/devolver")
def devolver_material_obra(
        obra_id: int,
        material_id: int,
        datos: schemas.SumarStockRequest,
        db: Session = Depends(get_db),
        usuario_actual: str = Depends(get_usuario_actual)
):
    # Validar jefe y empresa
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Solo los jefes pueden devolver material al almacén.")

    # Verificar que la obra es de su empresa
    obra = db.query(models.Obra).filter(
        models.Obra.id == obra_id,
        models.Obra.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada o sin acceso.")

    # Verificar material en la obra
    mat_obra = db.query(models.MaterialObra).filter(
        models.MaterialObra.obra_id == obra_id,
        models.MaterialObra.material_id == material_id
    ).first()

    if not mat_obra:
        raise HTTPException(status_code=404, detail="Material no encontrado en la obra.")

    if mat_obra.cantidad_asignada < datos.cantidad:
        raise HTTPException(status_code=400, detail="No puedes devolver más material del que hay en la obra.")

    mat_global = db.query(models.Material).filter(
        models.Material.id == material_id,
        models.Material.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not mat_global:
        raise HTTPException(status_code=404, detail="Error de integridad: El material no pertenece a tu almacén.")

    mat_obra.cantidad_asignada -= datos.cantidad
    mat_global.stock_total += datos.cantidad

    db.commit()
    return {"mensaje": "Material devuelto al almacén central correctamente."}


# endregion
# region RRHH

# ASIGNAR EMPLEADO A UNA OBRA
@router.post("/{obra_id}/empleados", response_model=schemas.ObraEmpleadoOut)
def asignar_empleado_a_obra(obra_id: int, asignacion: schemas.ObraEmpleadoCreate, db: Session = Depends(get_db),
                            usuario_actual: str = Depends(get_usuario_actual)):
    # 1. Usuario seguro
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)

    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden asignar empleados.")

    # 2. Comprobar que la obra existe Y es de su empresa
    obra = db.query(models.Obra).filter(
        models.Obra.id == obra_id,
        models.Obra.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada o sin acceso")

    # 3. Comprobar que el empleado existe Y es de su empresa
    empleado = db.query(models.Usuario).filter(
        models.Usuario.id == asignacion.empleado_id,
        models.Usuario.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado en tu empresa")

    # 4. Comprobar que no esté ya asignado
    asignacion_previa = db.query(models.ObraEmpleado).filter_by(
        obra_id=obra_id,
        empleado_id=asignacion.empleado_id
    ).first()

    if asignacion_previa:
        raise HTTPException(status_code=400, detail="Este empleado ya está asignado a esta obra")

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
def obtener_empleados_de_obra(obra_id: int, db: Session = Depends(get_db),
                              usuario_actual: str = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    # Validar que la obra pertenece a la empresa
    obra = db.query(models.Obra).filter(
        models.Obra.id == obra_id,
        models.Obra.empresa_id == usuario_logueado.empresa_id
    ).first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada o sin acceso")

    # Unir tablas filtrando que los usuarios sean de la misma empresa (doble check)
    empleados = db.query(models.Usuario).join(
        models.ObraEmpleado, models.Usuario.id == models.ObraEmpleado.empleado_id
    ).filter(
        models.ObraEmpleado.obra_id == obra_id,
        models.Usuario.empresa_id == usuario_logueado.empresa_id
    ).all()

    return empleados


# PANEL JEFE: ESTADÍSTICAS GENERALES (Filtrado por Empresa)
@router.get("/estadisticas/panel-jefe")
def obtener_estadisticas_panel(db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)

    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo para JEFES.")

    hoy = date.today()
    emp_id = jefe_logueado.empresa_id


    obras_activas = db.query(models.Obra).filter(
        models.Obra.empresa_id == emp_id,
        (models.Obra.fecha_fin == None) | (models.Obra.fecha_fin >= hoy)
    ).count()

    personal_total = db.query(models.Usuario).filter(
        models.Usuario.empresa_id == emp_id,
        models.Usuario.rol == "EMPLEADO"
    ).count()

    vehiculos_uso = db.query(models.Vehiculo).filter(
        models.Vehiculo.empresa_id == emp_id,
        models.Vehiculo.estado == "EN_USO"
    ).count()

    # Últimas 3 obras solo de su empresa
    ultimas_obras = db.query(models.Obra).filter(
        models.Obra.empresa_id == emp_id
    ).order_by(models.Obra.id.desc()).limit(3).all()

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

        porcentaje = (tareas_completadas / total_tareas) if total_tareas > 0 else 0.0
        progreso_obras.append({"nombre": obra.nombre, "progreso": porcentaje})

    vehiculos_disponibles = db.query(models.Vehiculo).filter(
        models.Vehiculo.empresa_id == emp_id,
        models.Vehiculo.estado == "DISPONIBLE"
    ).count()

    vehiculos_taller = db.query(models.Vehiculo).filter(
        models.Vehiculo.empresa_id == emp_id,
        models.Vehiculo.estado == "TALLER"
    ).count()

    # Personal ocupado: Solo empleados de su empresa que estén en su tabla de asignaciones
    personal_ocupado = db.query(models.ObraEmpleado).join(
        models.Obra, models.ObraEmpleado.obra_id == models.Obra.id
    ).filter(
        models.Obra.empresa_id == emp_id
    ).distinct(models.ObraEmpleado.empleado_id).count()

    obras_finalizadas = db.query(models.Obra).filter(
        models.Obra.empresa_id == emp_id,
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
