import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app import models, database

# Cargar las variables del .env
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# Configuración del encriptador de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Lector de tarjetas
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")


def get_password_hash(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_usuario_actual(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(database.get_db)
):
    error_credenciales = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No tienes permiso o tu sesión ha caducado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise error_credenciales
    except JWTError:
        raise error_credenciales

    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()

    if usuario is None:
        raise error_credenciales

    return usuario


def obtener_usuario_seguro(db: Session, usuario_actual):
    if isinstance(usuario_actual, models.Usuario):
        return usuario_actual

    email_usuario = usuario_actual["email"] if isinstance(usuario_actual, dict) else usuario_actual
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email_usuario).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

