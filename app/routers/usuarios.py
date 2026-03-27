# ENDPOINT USUARIOS
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_usuario_actual
from app.database import SessionLocal
from app import models, schemas
from app.utils.security import get_password_hash
from typing import List

# ROUTER USUARIOS
router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@router.post("/registro", response_model=schemas.UsuarioOut)
def crear_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # Comprobar si el email existe
    usuario_existente = db.query(models.Usuario).filter_by(email=usuario.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    # Encriptar la contraseña
    hashed_password = get_password_hash(usuario.password)

    # Crear el nuevo usuario
    nuevo_usuario = models.Usuario(
        nombre=usuario.nombre,
        apellidos=usuario.apellidos,
        email=usuario.email,
        password_hash=hashed_password,
        rol=usuario.rol
    )

    # Guardar en la base de datos
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return nuevo_usuario

#Identificar usuario
@router.get("/me", response_model=schemas.UsuarioOut)
def obtener_mi_perfil(
        db: Session = Depends(get_db),
        email_actual: str = Depends(get_usuario_actual)  # Leemos el token
):
    # Buscar en la BD al usuario dueño de ese email
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email_actual).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return usuario

# Ver un solo usuario en concreto por su ID
@router.get("/{usuario_id}", response_model=schemas.UsuarioOut)
def obtener_usuario_concreto(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter_by(id=usuario_id).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return usuario


# Borrar usuario
@router.delete("/{usuario_id}")
def eliminar_usuario(
        usuario_id: int,
        db: Session = Depends(get_db),
        usuario_actual: str = Depends(get_usuario_actual)
):
    # Busca en la base de datos al usuario actual
    jefe_en_potencia = db.query(models.Usuario).filter(models.Usuario.email == usuario_actual).first()

    # Comprobar si su rol es "JEFE"
    if jefe_en_potencia.rol.value != "JEFE":
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado: Solo el JEFE puede sacar a los empleados de la obra."
        )

    # Busca al usuario para borrarlo.
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.delete(usuario)
    db.commit()

    return {"mensaje": f"El usuario con ID {usuario_id} ha sido eliminado del sistema"}


@router.get("/", response_model=List[schemas.UsuarioOut])
def obtener_usuarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Buscar todos los usuarios en la base de datos
    usuarios = db.query(models.Usuario).offset(skip).limit(limit).all()
    return usuarios

@router.get("/", response_model=List[schemas.UsuarioOut])
def obtener_usuarios(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(get_usuario_actual)
):
    # Buscar todos los usuarios en la base de datos
    usuarios = db.query(models.Usuario).offset(skip).limit(limit).all()
    return usuarios
