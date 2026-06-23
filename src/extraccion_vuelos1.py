import os
import json
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
from opensky_api import OpenSkyApi

# Configuración de Logs
archivo_log = "pipeline_extraction1.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(archivo_log, encoding="utf-8"), logging.StreamHandler()],
)

def extraccion_vuelos():
    logging.info("🚀 Iniciando Extracción de Aeropuertos.")

    # --- Carga de credenciales ---
    archivo_credenciales = "credenciales_osky.json"
    if not os.path.exists(archivo_credenciales):
        logging.error(f"❌ Error Crítico: No se encuentra '{archivo_credenciales}'")
        return

    try:
        with open(archivo_credenciales, "r", encoding="utf-8") as f:
            credenciales = json.load(f)
            usuario_osky = credenciales.get("clientId")
            pass_osky = credenciales.get("clientSecret")
    except Exception as e:
        logging.error(f"❌ Error al leer 'credenciales_osky.json': {e}")
        return

    # --- Carga del nuevo Maestro  ---
    master_aeropuertos = "src/master_aeropuertos.csv"
    if not os.path.exists(master_aeropuertos):
        logging.error(f"❌ Error: No existe el maestro '{master_aeropuertos}'. Ejecuta generador_aeropuertos.py.")
        return

    try:
        df_master = pd.read_csv(master_aeropuertos)
        # Creamos conjuntos (sets) rápidos en memoria para identificar qué es UE y qué no
        aeropuertos_eu = set(df_master[df_master['is_ue'] == 1]['ident'].tolist())
        aeropuertos_global = set(df_master['ident'].tolist())
        logging.info(f"📋 Maestro cargado: {len(aeropuertos_global)} aeropuertos mundiales ({len(aeropuertos_eu)} pertenecen a la UE).")
    except Exception as e:
        logging.error(f"❌ Error al procesar el maestro: {e}")
        return

    # Inicializar API OpenSky
    if usuario_osky and pass_osky:
        api = OpenSkyApi(client_id=usuario_osky, client_secret=pass_osky)
        logging.info("🔐 Conectado a OpenSky con OAuth2.")
    else:
        api = OpenSkyApi()
        logging.warning("🔓 Conectado de forma anónima.")

    # Ventana de tiempo: Ayer completo (n-1)
    hoy_utc = datetime.now(timezone.utc)
    ayer = hoy_utc - timedelta(days=1)
    dia_ini = datetime(ayer.year, ayer.month, ayer.day, 0, 0, 0, tzinfo=timezone.utc)
    
    vuelos_raw = []

    # Descarga en 12 bloques de 2 horas
    for i in range(12):
        bloque_ini = dia_ini + timedelta(hours=i*2)
        bloque_fin = bloque_ini + timedelta(hours=2)
        
        ini_ts = int(bloque_ini.timestamp())
        fin_ts = int(bloque_fin.timestamp())
        
        logging.info(f"⏳ Descargando bloque {i+1}/12 ({bloque_ini.strftime('%H:%M')} a {bloque_fin.strftime('%H:%M')} UTC)...")
        
        try:
            vuelos = api.get_flights_from_interval(ini_ts, fin_ts)
            if vuelos is None:
                logging.warning(f"⚠️ Bloque {i+1} vacío. Saltando...")
                continue
                
            contador_vuelos = len(vuelos_raw)
            
            for vuelo in vuelos:
                salida = vuelo.estDepartureAirport
                llegada = vuelo.estArrivalAirport
                
                # REGLA DE EXTRACCIÓN GLOBAL:
                # Caso A: Salió de la UE (Vuelos n-1)
                # Caso B: Llegó a la UE desde fuera (Vuelos que pudieron salir en n-2 de América/Asia)
                salida_en_eu = salida in aeropuertos_eu
                llegada_en_eu = llegada in aeropuertos_eu
                
                if salida_en_eu or (llegada_en_eu and not salida_en_eu):
                    vuelos_raw.append({
                        "icao24": vuelo.icao24,
                        "firstSeen": vuelo.firstSeen,
                        "estDepartureAirport": salida,
                        "lastSeen": vuelo.lastSeen,
                        "estArrivalAirport": llegada,
                        "callsign": vuelo.callsign.strip() if vuelo.callsign else None,
                        "estDepartureAirportHorizDistance": vuelo.estDepartureAirportHorizDistance,
                        "estDepartureAirportVertDistance": vuelo.estDepartureAirportVertDistance,
                        "estArrivalAirportHorizDistance": vuelo.estArrivalAirportHorizDistance,
                        "estArrivalAirportVertDistance": vuelo.estArrivalAirportVertDistance,
                        "departureAirportCandidatesCount": vuelo.departureAirportCandidatesCount,
                        "arrivalAirportCandidatesCount": vuelo.arrivalAirportCandidatesCount,
                    })
            
            logging.info(f"  ✅ Capturados {len(vuelos_raw) - contador_vuelos} vuelos brutos de interés en este bloque.")
                    
        except Exception as e:
            logging.error(f"❌ Error en bloque {i+1}: {e}")
            return

    # Guardar los datos extraídos al almacenamiento local bruto (Raw Storage)
    if vuelos_raw:
        df_final = pd.DataFrame(vuelos_raw)
        os.makedirs("data", exist_ok=True)
        fichero_salida = "data/extraccion_vuelos1.csv"
        df_final.to_csv(fichero_salida, index=False)
        logging.info(f"📦 ¡Fase 1 Terminada! Almacenados {len(df_final)} vuelos brutos totales en '{fichero_salida}'.")
    else:
        logging.warning("⚠️ No se encontraron vuelos que cumplieran los criterios de extracción.")

if __name__ == "__main__":
    extraccion_vuelos()