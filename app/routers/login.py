from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app import auth

router = APIRouter(
    prefix="/login",
    tags=["Autenticación"]
)


@router.post("/")
def login(credenciales: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == credenciales.username).first()

    # Si el usuario no existe, o la contraseña no coincide con el Hash de la BDse echa
    if not usuario or not auth.verify_password(credenciales.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Si es correcto, se fabrica el Token de Acceso
    token = auth.create_access_token(data={"sub": usuario.email, "rol": usuario.rol.name})

    # Se lo devolvemos al usuario
    return {"access_token": token, "token_type": "bearer"}