from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import SessionLocal, get_db
from app import models, schemas
from app.auth import get_usuario_actual, obtener_usuario_seguro
from app.schemas import SumarStockRequest

router = APIRouter(prefix="/materiales", tags=["Materiales"])

# CREAR MATERIAL
@router.post("/", response_model=schemas.MaterialOut)
def crear_material(material: schemas.MaterialBase, db: Session = Depends(get_db),
                   usuario_actual: dict = Depends(get_usuario_actual)):
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403,    
                            detail="Acceso denegado: Solo los JEFES pueden añadir materiales al almacén.")

    # Guardamos el material asignándole el ID de la empresa del jefe
    nuevo_material = models.Material(**material.model_dump(), empresa_id=jefe_logueado.empresa_id)
    db.add(nuevo_material)
    db.commit()
    db.refresh(nuevo_material)
    return nuevo_material


# VER TODOS LOS MATERIALES
@router.get("/", response_model=List[schemas.MaterialOut])
def obtener_materiales(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                       usuario_actual: dict = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)
    # Filtramos por el ID de la empresa
    return db.query(models.Material).filter(models.Material.empresa_id == usuario_logueado.empresa_id).offset(
        skip).limit(limit).all()


# VER UN SOLO MATERIAL POR ID
@router.get("/{material_id}", response_model=schemas.MaterialOut)
def obtener_material(material_id: int, db: Session = Depends(get_db),
                     usuario_actual: dict = Depends(get_usuario_actual)):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)

    material = db.query(models.Material).filter(
        models.Material.id == material_id,
        models.Material.empresa_id == usuario_logueado.empresa_id
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado o no pertenece a tu empresa")
    return material


# ACTUALIZAR MATERIAL
@router.put("/{material_id}", response_model=schemas.MaterialOut)
def actualizar_material(material_id: int, material_actualizado: schemas.MaterialBase, db: Session = Depends(get_db),
                        usuario_actual: dict = Depends(get_usuario_actual)):
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden modificar materiales.")

    material = db.query(models.Material).filter(
        models.Material.id == material_id,
        models.Material.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado o no pertenece a tu empresa")

    for clave, valor in material_actualizado.model_dump().items():
        setattr(material, clave, valor)

    db.commit()
    db.refresh(material)
    return material


# SUMAR STOCK MATERIAL
@router.post("/{material_id}/sumar-stock", response_model=schemas.MaterialOut)
def sumar_stock_material(
        material_id: int,
        datos: SumarStockRequest,
        db: Session = Depends(get_db),
        usuario_actual: dict = Depends(get_usuario_actual)
):
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden modificar el stock.")

    material = db.query(models.Material).filter(
        models.Material.id == material_id,
        models.Material.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado o no pertenece a tu empresa")

    material.stock_total += datos.cantidad

    db.commit()
    db.refresh(material)

    return material


# BORRAR MATERIAL
@router.delete("/{material_id}")
def eliminar_material(material_id: int, db: Session = Depends(get_db),
                      usuario_actual: dict = Depends(get_usuario_actual)):
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403,
                            detail="Acceso denegado: Solo los JEFES pueden borrar materiales del almacén.")

    material = db.query(models.Material).filter(
        models.Material.id == material_id,
        models.Material.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado o no pertenece a tu empresa")

    db.delete(material)
    db.commit()

    return {"mensaje": f"El material con ID {material_id} ha sido eliminado correctamente del inventario"}