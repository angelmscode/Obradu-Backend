from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import usuarios, obras, materiales, vehiculos, asistencias, login

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ObraDu API",
    description="Backend profesional para gestión de obras"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://cloning-sullen-eel.ngrok-free.dev"],
    allow_origin_regex=r"http://localhost:.*",  # Acepta cualquier puerto de localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Conectamos las rutas al núcleo de la app
app.include_router(usuarios.router)
app.include_router(obras.router)
app.include_router(vehiculos.router)
app.include_router(asistencias.router)
app.include_router(login.router)
app.include_router(materiales.router)

@app.get("/")
def inicio():
    return {"mensaje": "¡El servidor de ObraDu está corriendo!"}