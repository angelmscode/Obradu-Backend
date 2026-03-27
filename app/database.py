import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker, declarative_base

# Cargar las variables del .env
load_dotenv()

# Coger la URL del .env
URL_BASE_DATOS = os.getenv("DATABASE_URL")

# Motor de la base de datos
engine = create_engine(URL_BASE_DATOS)

# Creador de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Clase base
Base = declarative_base()