import os
import logging
from google.cloud import bigquery

# Configuración de Logs profesional para tu TFM
archivo_log = "pipeline_load_bronze.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(archivo_log, encoding="utf-8"), logging.StreamHandler()],
)

# Inyectamos la ruta del JSON de Google Cloud en las variables de entorno
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credenciales_gcp.json"

def cargar_csv_a_bigquery_bronze():
    logging.info("📤 [CAPA BRONZE] Iniciando carga incremental a BigQuery.")
    
    # Validación de seguridad de la clave
    if not os.path.exists("credenciales_gcp.json"):
        logging.error("❌ Error Crítico: No se encontró 'credenciales_gcp.json' en la raíz.")
        return

    try:
        # Inicializa el cliente de BigQuery detectando automáticamente el proyecto de tu JSON
        client = bigquery.Client()
        
        # --- CONFIGURACIÓN DE TU ARQUITECTURA ---
        # Cambia "bronze" por "bronce" si lo creaste en español en tu consola
        DATASET_ID = "Bronze"  
        TABLE_ID = "vuelos_raw"   # Nombre de la tabla bruta dentro del dataset
        TABLA_REFERENCIA = f"{client.project}.{DATASET_ID}.{TABLE_ID}"
        
        RUTA_CSV = "data/vuelos_brutos.csv"
        
        if not os.path.exists(RUTA_CSV):
            logging.error(f"❌ Error: No existe el archivo '{RUTA_CSV}'. Ejecuta primero el script de extracción.")
            return

        # Configuración del Job de Carga
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,  # Ignora la cabecera del CSV
            autodetect=True,      # BigQuery infiere los tipos de datos (esquema dinámico)
            # ESTRATEGIA: Carga incremental. Añade al final sin borrar el histórico
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND 
        )
        
        logging.info(f"⏳ Subiendo '{RUTA_CSV}' de forma incremental a la tabla '{TABLA_REFERENCIA}'...")
        
        # Lectura del archivo en binario y envío a GCP
        with open(RUTA_CSV, "rb") as source_file:
            load_job = client.load_table_from_file(
                source_file, 
                TABLA_REFERENCIA, 
                job_config=job_config
            )
        
        # Bloquea la consola hasta que BigQuery procese el archivo en la nube
        load_job.result()  
        
        logging.info(f"✅ [Fase Bronze Completada] Datos inyectados con éxito en '{DATASET_ID}.{TABLE_ID}'.")
        
    except Exception as e:
        logging.error(f"❌ Error durante la carga a BigQuery: {e}")

if __name__ == "__main__":
    cargar_csv_a_bigquery_bronze()