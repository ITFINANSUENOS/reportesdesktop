from fastapi import FastAPI
# Importamos las nuevas rutas asíncronas
from src.api.procesamiento_route import router as procesamiento_router

app = FastAPI(
    title="API de Procesamiento de Reportes Financieros (Asíncrona)",
    description="Procesa archivos pesados de Datacrédito y CIFIN usando un flujo de S3 y tareas en segundo plano."
)

# Incluye las nuevas rutas de procesamiento
app.include_router(procesamiento_router, prefix="/api/v1")

# NO INCLUIR LA RUTA ANTIGUA
# ----------------------------------------------------
# app.include_router(datacredito_route.router, prefix="/api/v1") 
# ¡IMPORTANTE! Esta línea (si la tenías) debe ser eliminada.
# Es la que causa el error 502 Bad Gateway.
# ----------------------------------------------------


@app.get("/", tags=["Root"])
def read_root():
    """
    Endpoint de bienvenida.
    """
    return {"message": "Bienvenido a la API de Procesamiento de Reportes Asíncrona"}