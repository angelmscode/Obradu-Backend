# ENDPOINT USUARIOS
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_usuario_actual, obtener_usuario_seguro
from app.database import get_db
from app import models, schemas, auth
from app.utils.security import get_password_hash
from typing import List

# ROUTER USUARIOS
router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/registro", response_model=schemas.UsuarioOut)
def crear_usuario(
    usuario: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_usuario_actual)
):
    # Solo un JEFE puede registrar nuevos usuarios
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)
    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado: Solo los JEFES pueden registrar nuevos empleados."
        )

    # Comprobar si el email ya existe
    usuario_existente = db.query(models.Usuario).filter_by(email=usuario.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    # Encriptar la contraseña
    hashed_password = get_password_hash(usuario.password)

    # Crear el nuevo usuario asignándole la empresa del jefe que lo registra
    nuevo_usuario = models.Usuario(
        nombre=usuario.nombre,
        apellidos=usuario.apellidos,
        email=usuario.email,
        password_hash=hashed_password,
        rol=usuario.rol,
        empresa_id=jefe_logueado.empresa_id  # Hereda la empresa del jefe
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return nuevo_usuario


# Identificar usuario propio
@router.get("/me", response_model=schemas.UsuarioOut)
def obtener_mi_perfil(
    usuario_actual=Depends(auth.get_usuario_actual),
    db: Session = Depends(get_db)
):
    if isinstance(usuario_actual, models.Usuario):
        return usuario_actual

    email_actual = usuario_actual["email"] if isinstance(usuario_actual, dict) else usuario_actual
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email_actual).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


# Ver todos los usuarios de la empresa (requiere autenticación)
@router.get("/", response_model=List[schemas.UsuarioOut])
def obtener_usuarios(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_usuario_actual)
):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)
    # Solo devuelve usuarios de la misma empresa
    usuarios = db.query(models.Usuario).filter(
        models.Usuario.empresa_id == usuario_logueado.empresa_id
    ).offset(skip).limit(limit).all()
    return usuarios


# Ver un solo usuario en concreto por su ID
@router.get("/{usuario_id}", response_model=schemas.UsuarioOut)
def obtener_usuario_concreto(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_usuario_actual)
):
    usuario_logueado = obtener_usuario_seguro(db, usuario_actual)
    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == usuario_id,
        models.Usuario.empresa_id == usuario_logueado.empresa_id
    ).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


# Borrar usuario
@router.delete("/{usuario_id}")
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_usuario_actual)
):
    jefe_logueado = obtener_usuario_seguro(db, usuario_actual)

    if jefe_logueado.rol.value != "JEFE":
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado: Solo el JEFE puede eliminar empleados."
        )

    # Solo puede borrar usuarios de su propia empresa
    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == usuario_id,
        models.Usuario.empresa_id == jefe_logueado.empresa_id
    ).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.delete(usuario)
    db.commit()

    return {"mensaje": f"El usuario con ID {usuario_id} ha sido eliminado del sistema"}