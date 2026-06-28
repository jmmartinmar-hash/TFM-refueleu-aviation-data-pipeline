import os
import json
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
from opensky_api import OpenSkyApi

# Configuración de Logs profesional para el seguimiento del TFM
archivo_log = "pipeline_extraction_vuelos.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(archivo_log, encoding="utf-8"), logging.StreamHandler()],
)

def cargar_credenciales(ruta_json="credenciales_osky.json"):
    """Carga de credenciales del archivo JSON oficial de la API."""
    if not os.path.exists(ruta_json):
        logging.error(f"❌ Error Crítico: No se encuentra '{ruta_json}'")
        return None, None
    try:
        with open(ruta_json, "r", encoding="utf-8") as f:
            credenciales = json.load(f)
            return credenciales.get("clientId"), credenciales.get("clientSecret")
    except Exception as e:
        logging.error(f"❌ Error al leer '{ruta_json}': {e}")
        return None, None

def extraer_vuelos_mvp():
    logging.info("🚀 [ENTIDAD 1] Iniciando extracción aislada de Vuelos Brutos.")

    # 1. Autenticación utilizando la librería oficial
    usuario_osky, pass_osky = cargar_credenciales()
    if usuario_osky and pass_osky:
        api = OpenSkyApi(client_id=usuario_osky, client_secret=pass_osky)
        logging.info("🔐 Conectado a OpenSky Network mediante OAuth2 encapsulado.")
    else:
        logging.warning("🔓 Credenciales no válidas. Intentando conexión anónima (Cuota muy reducida).")
        api = OpenSkyApi()

    # 2. Definición del intervalo de tiempo (Prueba controlada de 2 horas de AYER)
    hoy_utc = datetime.now(timezone.utc)
    ayer = hoy_utc - timedelta(days=1)
    
    # Fijamos un bloque de 2 horas (de 00:00 a 02:00 UTC de ayer) para asegurar datos estables
    bloque_ini = datetime(ayer.year, ayer.month, ayer.day, 0, 0, 0, tzinfo=timezone.utc)
    bloque_fin = bloque_ini + timedelta(hours=2)
    
    ini_ts = int(bloque_ini.timestamp())
    fin_ts = int(bloque_fin.timestamp())
    
    logging.info(f"⏳ Solicitando intervalo: {bloque_ini.strftime('%Y-%m-%d %H:%M')} a {bloque_fin.strftime('%H:%M')} UTC...")
    
    vuelos_raw = []
    try:
        # Llamada al método oficial de la librería
        vuelos = api.get_flights_from_interval(ini_ts, fin_ts)
        
        if vuelos is None:
            logging.warning("⚠️ La API devolvió un conjunto vacío o se superó el Rate Limit.")
            return
            
        # 3. Procesamiento y aplanado de los objetos de la API a Diccionarios de Python
        for vuelo in vuelos:
            vuelos_raw.append({
                "icao24": vuelo.icao24,
                "firstSeen": vuelo.firstSeen,
                "estDepartureAirport": vuelo.estDepartureAirport,
                "lastSeen": vuelo.lastSeen,
                "estArrivalAirport": vuelo.estArrivalAirport,
                "callsign": vuelo.callsign.strip() if vuelo.callsign else None,
                "estDepartureAirportHorizDistance": vuelo.estDepartureAirportHorizDistance,
                "estDepartureAirportVertDistance": vuelo.estDepartureAirportVertDistance,
                "estArrivalAirportHorizDistance": vuelo.estArrivalAirportHorizDistance,
                "estArrivalAirportVertDistance": vuelo.estArrivalAirportVertDistance,
                "departureAirportCandidatesCount": vuelo.departureAirportCandidatesCount,
                "arrivalAirportCandidatesCount": vuelo.arrivalAirportCandidatesCount,
            })
            
        logging.info(f"✅ Descarga completada. Se recuperaron {len(vuelos_raw)} vuelos globales en este bloque.")
        
    except Exception as e:
        logging.error(f"❌ Error durante la consulta del intervalo: {e}")
        return

    # 4. Almacenamiento directo en la Landing Zone (Fase Bronze - Datos Crudos)
    if vuelos_raw:
        df_final = pd.DataFrame(vuelos_raw)
        
        # Creamos la carpeta de la arquitectura Medallion
        
        fichero_salida = "data/vuelos_brutos.csv"
        
        df_final.to_csv(fichero_salida, index=False)
        logging.info(f"💾 [Fase Bronze] Guardados {len(df_final)} registros crudos en: '{fichero_salida}'")
    else:
        logging.warning("⚠️ No se recuperaron datos de vuelos en el periodo seleccionado.")

if __name__ == "__main__":
    extraer_vuelos_mvp()