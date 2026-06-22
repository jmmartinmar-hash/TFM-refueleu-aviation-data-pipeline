import os
import json
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
from opensky_api import OpenSkyApi

# =====================================================================
# 1. CONFIGURACIÓN DE LOGS
# =====================================================================
log_filename = "pipeline_extraction.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(log_filename, encoding="utf-8"), logging.StreamHandler()],
)

# =====================================================================
# 2. PROCESO PRINCIPAL DE EXTRACCIÓN OPTIMIZADO
# =====================================================================
def extract_eu_departures():
    logging.info("🚀 Iniciando Fase 1 de Extracción (Estrategia Descarga Masiva + Filtro Local).")

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

    # --- CARGA DE TODOS LOS AEROPUERTOS DE LA UE ---
    airports_path = "Eu_airport.csv"
    if not os.path.exists(airports_path):
        logging.error(f"❌ Error Crítico: No existe '{airports_path}'. Ejecuta primero 'src/generate_airports.py'")
        return

    try:
        df_airports = pd.read_csv(airports_path, header=None)
        # Usamos un 'set' (conjunto) porque la búsqueda indexada en sets es infinitamente más rápida que en listas
        eu_airports = set(df_airports[0].dropna().astype(str).str.strip().tolist())
        logging.info(f"📋 Cargados {len(eu_airports)} aeropuertos oficiales de la UE para filtrado.")
    except Exception as e:
        logging.error(f"❌ Error al procesar '{airports_path}': {e}")
        return

    # --- INICIALIZACIÓN DE API (CORREGIDA) ---
    if opensky_user and opensky_pass:
        # 🔥 CAMBIO CRÍTICO: Pasamos los parámetros nombrados explícitamente para OAuth2
        api = OpenSkyApi(client_id=opensky_user, client_secret=opensky_pass)
        logging.info("🔐 Conectado a OpenSky usando credenciales autenticadas (OAuth2).")
    else:
        api = OpenSkyApi()
        logging.warning("🔓 Conectado de forma anónima (Sujeto a fuertes límites de tráfico).")

    # --- VENTANA DE TIEMPO (Día anterior completo) ---
    now_utc = datetime.now(timezone.utc)
    yesterday = now_utc - timedelta(days=1)
    day_start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, tzinfo=timezone.utc)
    
    all_flights_raw = []
    logging.info(f"📅 Procesando fecha completa: {day_start.strftime('%Y-%m-%d')}")

    # Dividimos las 24 horas del día en 12 bloques de 2 horas (requerido por las limitaciones de OpenSky para /flights/all)
    for i in range(12):
        block_start = day_start + timedelta(hours=i*2)
        block_end = block_start + timedelta(hours=2)
        
        start_ts = int(block_start.timestamp())
        end_ts = int(block_end.timestamp())
        
        logging.info(f"⏳ Descargando bloque {i+1}/12: Desde {block_start.strftime('%H:%M')} hasta {block_end.strftime('%H:%M')} UTC...")
        
        try:
            # Descarga masiva de todos los vuelos registrados en el mundo en este intervalo
            flights = api.get_flights_from_interval(start_ts, end_ts)
            
            if flights is None:
                logging.warning(f"⚠️ El bloque {i+1} no devolvió datos (posible saturación temporal). Saltando...")
                continue
                
            logging.info(f"  📥 Recibidos {len(flights)} vuelos globales. Filtrando por aeropuertos de la UE...")
            
            # Filtramos localmente en memoria de forma ultra rápida
            for flight in flights:
                if flight.estDepartureAirport in eu_airports:
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
            logging.error(f"❌ Error crítico en el bloque {i+1}: {e}")
            return

    # --- EXPORTACIÓN A RAW ---
    if all_flights_raw:
        df_output = pd.DataFrame(all_flights_raw)
        os.makedirs("data", exist_ok=True)
        output_path = "data/raw_departures.csv"

        df_output.to_csv(output_path, index=False)
        logging.info(f"📦 ¡Fase Finalizada! Guardados {len(df_output)} vuelos totales de la UE en '{output_path}'.")
    else:
        logging.warning("⚠️ No se extrajo ningún vuelo coincidente para la lista completa de la UE.")

if __name__ == "__main__":
    extract_eu_departures()