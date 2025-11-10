# --- Pega esto en tu Dockerfile ---

# 1. Usa una imagen base oficial de Python 3.11
FROM python:3.11-slim

# 2. Establece el directorio de trabajo DENTRO del contenedor
WORKDIR /app

# 3. Instala las dependencias
COPY requirements.txt .

# --- ¡ESTA ES LA LÍNEA NUEVA QUE ARREGLA EL ERROR! ---
# Actualizamos pip ANTES de instalar los requirements
RUN pip install --upgrade pip

# Ahora este comando usará el pip actualizado y encontrará los paquetes
RUN pip install --no-cache-dir -r requirements.txt

# --- Etapa 4: Copia de tu Código ---
# ¡CAMBIO 1: Copiamos ambos, src Y main_api.py!
COPY ./src ./src
COPY main_api.py .

# --- Etapa 5: Comando de Ejecución ---
# ¡CAMBIO 2: Apuntamos a main_api.py!
# Le decimos a Uvicorn que ejecute el archivo 'main_api'
# y busque la variable 'app' dentro de él.
CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8000"]