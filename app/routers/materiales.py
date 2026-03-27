from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import SessionLocal
from app import models, schemas
from app.auth import get_usuario_actual

router = APIRouter(prefix="/materiales", tags=["Materiales"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# CREAR MATERIAL
@router.post("/", response_model=schemas.MaterialOut)
def crear_material(material: schemas.MaterialBase, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden añadir materiales al almacén.")

    nuevo_material = models.Material(**material.model_dump())
    db.add(nuevo_material)
    db.commit()
    db.refresh(nuevo_material)
    return nuevo_material


# VER TODOS LOS MATERIALES
@router.get("/", response_model=List[schemas.MaterialOut])
def obtener_materiales(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    return db.query(models.Material).offset(skip).limit(limit).all()


# VER UN SOLO MATERIAL POR ID
@router.get("/{material_id}", response_model=schemas.MaterialOut)
def obtener_material(material_id: int, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    material = db.query(models.Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    return material


# ACTUALIZAR MATERIAL
@router.put("/{material_id}", response_model=schemas.MaterialOut)
def actualizar_material(material_id: int, material_actualizado: schemas.MaterialBase, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden modificar materiales.")

    material = db.query(models.Material).filter_by(id=material_id).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    for clave, valor in material_actualizado.model_dump().items():
        setattr(material, clave, valor)

    db.commit()
    db.refresh(material)
    return material


# BORRAR MATERIAL
@router.delete("/{material_id}")
def eliminar_material(material_id: int, db: Session = Depends(get_db), usuario_actual: str = Depends(get_usuario_actual)):
    jefe_logueado = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los JEFES pueden borrar materiales del almacén.")

    material = db.query(models.Material).filter_by(id=material_id).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    db.delete(material)
    db.commit()

    return {"mensaje": f"El material con ID {material_id} ha sido eliminado correctamente del inventario"}
