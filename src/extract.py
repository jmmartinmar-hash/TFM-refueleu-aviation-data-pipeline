import os
import json
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
from opensky_api import OpenSkyApi

# =====================================================================
# 1. CONFIGURACIÓN DE LOGS (Registro local de todo lo que pasa)
# =====================================================================
log_filename = "pipeline_extraction.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(log_filename, encoding="utf-8"), logging.StreamHandler()],
)

# =====================================================================
# 2. PROCESO PRINCIPAL DE EXTRACCIÓN (STAGE 1)
# =====================================================================
def extract_eu_departures():
    logging.info("🚀 Iniciando Fase 1 de Extracción: Vuelos de salida de la UE.")

    # --- CARGA DE CREDENCIALES ---
    credentials_path = "credentials.json"
    if not os.path.exists(credentials_path):
        logging.error(f"❌ Error Crítico: No se encuentra el archivo de credenciales en '{credentials_path}'")
        return

    try:
        with open(credentials_path, "r", encoding="utf-8") as f:
            creds = json.load(f)
            opensky_user = creds.get("clientId")
            opensky_pass = creds.get("clientSecret")
            
    except Exception as e:
        logging.error(f"❌ Error al leer 'credentials.json': {e}")
        return

    # --- CARGA DE AEROPUERTOS ---
    airports_path = "Eu_airport.csv"
    if not os.path.exists(airports_path):
        logging.error(f"❌ Error Crítico: No se encuentra el archivo de aeropuertos en '{airports_path}'")
        return

    try:
        df_airports = pd.read_csv(airports_path, header=None)
        eu_airports = df_airports[0].dropna().astype(str).str.strip().tolist()
        logging.info(f"📋 Cargados {len(eu_airports)} aeropuertos desde '{airports_path}'.")
    except Exception as e:
        logging.error(f"❌ Error al procesar '{airports_path}': {e}")
        return

    # --- CÁLCULO DE VENTANA DE TIEMPO (Día n-1 en UTC) ---
    now_utc = datetime.now(timezone.utc)
    yesterday = now_utc - timedelta(days=1)
    
    start_date = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, tzinfo=timezone.utc)
    end_date = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59, tzinfo=timezone.utc)
    
    start_timestamp = int(start_date.timestamp())
    end_timestamp = int(end_date.timestamp())

    logging.info(f"📅 Ventana de tiempo a auditar: Desde {start_date} hasta {end_date}")

    # --- INICIALIZACIÓN DE API ---
    if opensky_user and opensky_pass:
        api = OpenSkyApi(opensky_user, opensky_pass)
        logging.info("🔐 Conectado a OpenSky usando el clientId y clientSecret del archivo JSON.")
    else:
        api = OpenSkyApi()
        logging.warning("🔓 Conectado de forma anónima (Sujeto a fuertes límites de tráfico).")

    all_flights_raw = []

    # --- BUCLE DE EXTRACCIÓN ---
    for airport in eu_airports:
        logging.info(f"✈️ Solicitando despegues desde {airport}...")
        try:
            departures = api.get_departures_of_airport(airport, start_timestamp, end_timestamp)

            if departures is None:
                logging.warning(f"⚠️ OpenSky no devolvió datos para {airport} (Sin vuelos o límite alcanzado).")
                continue

            logging.info(f"✅ Extraídos {len(departures)} vuelos desde {airport}.")

            for flight in departures:
                all_flights_raw.append({
                    "icao24": flight.icao24,
                    "firstSeen": flight.firstSeen,
                    "estDepartureAirport": flight.estDepartureAirport,
                    "lastSeen": flight.lastSeen,
                    "estArrivalAirport": flight.estArrivalAirport,
                    "callsign": flight.callsign.strip() if flight.callsign else None,
                    "estDepartureAirportHorizDistance": flight.estDepartureAirportHorizDistance,
                    "estDepartureAirportVertDistance": flight.estDepartureAirportVertDistance,
                    "estArrivalAirportHorizDistance": flight.estArrivalAirportHorizDistance,
                    "estArrivalAirportVertDistance": flight.estArrivalAirportVertDistance,
                    "departureAirportCandidatesCount": flight.departureAirportCandidatesCount,
                    "arrivalAirportCandidatesCount": flight.arrivalAirportCandidatesCount,
                })

        except Exception as e:
            logging.error(f"❌ Error extrayendo datos del aeropuerto {airport}: {e}")
            return

    # --- EXPORTACIÓN A RAW ---
    if all_flights_raw:
        df_output = pd.DataFrame(all_flights_raw)
        os.makedirs("data", exist_ok=True)
        output_path = "data/raw_departures.csv"

        df_output.to_csv(output_path, index=False)
        logging.info(f"📦 Guardados con éxito {len(df_output)} vuelos brutos en '{output_path}'.")
        logging.info("🎉 Proceso finalizado correctamente.")
    else:
        logging.warning("⚠️ No se extrajo ningún vuelo para los aeropuertos indicados.")

if __name__ == "__main__":
    extract_eu_departures()