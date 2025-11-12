import boto3
import os
import shutil
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from src.api.datacredito_service import DataCreditoApiService  # ¡Usamos tu servicio!

# --- Configuración (¡Ajusta esto!) ---
router = APIRouter()
s3_client = boto3.client('s3', region_name='us-east-2') # Asegúrate de que la región sea la de tu bucket
BUCKET_NAME = 'electrocreditos-reportes-privados' # El nombre de tu bucket S3
# -------------------------------------


# Esta es la Tarea Pesada que se ejecuta en segundo plano
def procesar_archivos_en_segundo_plano(
    plano_key: str, 
    correcciones_key: str, 
    empresa: str,
    output_key: str
):
    """
    Esta función se ejecuta en segundo plano. NO sufre de timeouts de API.
    1. Descarga los archivos de S3.
    2. Llama a tu servicio de procesamiento.
    3. Sube el resultado a S3.
    """
    service_api = DataCreditoApiService()
    temp_dir = f"/tmp/{uuid.uuid4().hex}" # /tmp/ es escribible en App Runner
    os.makedirs(temp_dir, exist_ok=True)
    
    plano_path = os.path.join(temp_dir, plano_key)
    corrections_path = os.path.join(temp_dir, correcciones_key)
    output_path = os.path.join(temp_dir, output_key)

    try:
        # 1. Descargar archivos de S3
        print(f"BG_TASK: Descargando archivos a {temp_dir}...")
        s3_client.download_file(BUCKET_NAME, plano_key, plano_path)
        s3_client.download_file(BUCKET_NAME, correcciones_key, corrections_path)
        print("BG_TASK: Archivos descargados.")

        # 2. Llamar a tu lógica de servicio (tu código)
        print(f"BG_TASK: Iniciando procesamiento para la empresa {empresa}...")
        service_api.process_files_for_api(
            plano_path=plano_path,
            correcciones_path=corrections_path,
            output_path=output_path,
            empresa=empresa
        )
        print("BG_TASK: Procesamiento completado.")

        # 3. Subir el resultado a S3
        s3_client.upload_file(output_path, BUCKET_NAME, f"resultados/{output_key}")
        print(f"BG_TASK: Resultado subido a S3 en 'resultados/{output_key}'.")

    except Exception as e:
        print(f"BG_TASK_ERROR: Falló el procesamiento. Error: {e}")
        # (Aquí deberías loguear a un servicio de monitoreo)
    
    finally:
        # 4. Limpiar carpeta temporal
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"BG_TASK: Carpeta temporal {temp_dir} eliminada.")


# --- ENDPOINT 1: Generar URLs de Subida ---
@router.post("/generar_urls_subida", tags=["Procesamiento"])
def generar_urls_subida(data: dict):
    """
    PASO 1: Pide permiso para subir.
    Recibe los nombres de los archivos y devuelve URLs pre-firmadas.
    """
    plano_filename = data.get("plano_filename")
    correcciones_filename = data.get("correcciones_filename")
    
    if not plano_filename or not correcciones_filename:
        raise HTTPException(status_code=400, detail="Se requieren ambos nombres de archivo")

    # Genera nombres de archivo únicos para S3 (evita colisiones)
    plano_key = f"uploads/{uuid.uuid4().hex}-{plano_filename}"
    correcciones_key = f"uploads/{uuid.uuid4().hex}-{correcciones_filename}"

    try:
        # Genera las URLs pre-firmadas (permiten 'PUT')
        url_plano = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': BUCKET_NAME, 'Key': plano_key},
            ExpiresIn=3600  # 1 hora
        )
        url_correcciones = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': BUCKET_NAME, 'Key': correcciones_key},
            ExpiresIn=3600  # 1 hora
        )
        
        return {
            "plano": {"upload_url": url_plano, "key": plano_key},
            "correcciones": {"upload_url": url_correcciones, "key": correcciones_key}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar URLs de S3: {e}")


# --- ENDPOINT 2: Iniciar Procesamiento ---
@router.post("/iniciar_procesamiento_datacredito", tags=["Procesamiento"])
def iniciar_procesamiento_datacredito(
    data: dict, 
    background_tasks: BackgroundTasks
):
    """
    PASO 3: Inicia el procesamiento.
    Recibe las 'keys' de S3 y la 'empresa', responde INMEDIATAMENTE 
    y deja el trabajo pesado en segundo plano.
    """
    plano_key = data.get("plano_key")
    correcciones_key = data.get("correcciones_key")
    empresa = data.get("empresa")
    
    if not all([plano_key, correcciones_key, empresa]):
        raise HTTPException(status_code=400, detail="Se requieren plano_key, correcciones_key y empresa")

    output_filename = f"Resultado_{empresa}_{plano_key.split('-')[-1]}"

    # ¡LA SOLUCIÓN AL 502!
    # 1. Añade el trabajo pesado a la cola de fondo
    background_tasks.add_task(
        procesar_archivos_en_segundo_plano, 
        plano_key, 
        correcciones_key, 
        empresa, 
        output_filename
    )
    
    # 2. Responde INMEDIATAMENTE
    return {
        "status": "accepted",
        "message": "El procesamiento ha comenzado en segundo plano.",
        "output_key": f"resultados/{output_filename}"
    }