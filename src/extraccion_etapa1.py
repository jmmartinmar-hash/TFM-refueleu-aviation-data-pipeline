import os
import json
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
from opensky_api import OpenSkyApi

# =====================================================================
# 1. CONFIGURACIÓN DE LOGS
# =====================================================================
log = "pipeline_extraction1.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(log, encoding="utf-8"), logging.StreamHandler()],
)

# ===============================================================================
# 2. PROCESO PRINCIPAL DE EXTRACCIÓN DE VUELOS CON SALIDA EN AEROPUERTOS DE LA UE
# ===============================================================================
def extraccion_eu_salidas():
    logging.info("Iniciando Extracción: Descarga de vuelos de la UE desde OpenSky API...")

    # --- CARGA DE CREDENCIALES OPENSKY EN FICHERO CREDENCIALES ---
    credenciales = "credenciales_osky.json"
    if not os.path.exists(credenciales):
        logging.error(f"Error: No se encuentra el archivo de credenciales en '{credenciales}'")
        return

    try:
        with open(credenciales, "r", encoding="utf-8") as f:
            creds = json.load(f)
            usuario_osky = creds.get("clientId")
            password_osky = creds.get("clientSecret")
    except Exception as e:
        logging.error(f"Error al leer 'credenciales_osky.json': {e}")
        return

    # --- CARGA DE TODOS LOS AEROPUERTOS DE LA UE DESDE FICHERO aeropuertos_eu.csv ---
    aeropuertos = "aeropuertos_eu.csv"
    if not os.path.exists(aeropuertos):
        #registro en el log del error  por falta de fichero de aeropuertos
        logging.error(f"Error Crítico: No existe '{aeropuertos}'. Ejecutar primero 'src/generate_airports.py'")
        return

    try:
        df_aeropuertos = pd.read_csv(aeropuertos, header=None)
        eu_aeropuertos = set(df_aeropuertos[0].dropna().astype(str).str.strip().tolist())
        #registro en el log del número de aeropuertos cargados
        logging.info(f"Cargados {len(eu_aeropuertos)} aeropuertos oficiales de la UE.")
    except Exception as e:
        #registro en el log del error crítico al procesar el fichero de aeropuertos
        logging.error(f"Error al procesar '{aeropuertos}': {e}")
        return

    # --- INICIALIZACIÓN DE API ---
    if usuario_osky and password_osky:
        # Paso los parámetros nombrados explícitamente para OAuth2
        api = OpenSkyApi(client_id=usuario_osky, client_secret=password_osky)
        logging.info("Conectado a OpenSky con credenciales...")
    else:
        api = OpenSkyApi()
        logging.warning("Conectado de forma anónima...")

    # ---Descarga de vuelos del Día anterior completo ---
    hoy = datetime.now(timezone.utc)
    ayer = hoy - timedelta(days=1)
    dia_ini = datetime(ayer.year, ayer.month, ayer.day, 0, 0, 0, tzinfo=timezone.utc)
    
    vuelos = []
    logging.info(f"Procesando fecha completa: {dia_ini.strftime('%Y-%m-%d')}")

    # La descarga se realiza en bloques de 2 horas para evitar saturación y errores de timeout
    for i in range(12):
        bloque_ini = dia_ini + timedelta(hours=i*2)
        bloque_fin = bloque_ini + timedelta(hours=2)
        
        inicio_ts = int(bloque_ini.timestamp())
        fin_ts = int(bloque_fin.timestamp())
        
        logging.info(f"Descargando bloque {i+1}/12: Desde {bloque_ini.strftime('%H:%M')} hasta {bloque_fin.strftime('%H:%M')} UTC...")
        
        try:
            # Descarga masiva de todos los vuelos registrados en el mundo en el intervalo de tiempo especificado
            flights = api.get_flights_from_interval(inicio_ts, fin_ts)
            #resgistra en el log el número de vuelos obtenidos en el bloque o fallo en descarga de bloque 
            if flights is None:
                logging.warning(f"El bloque {i+1} no devolvió datos, Continuando con el siguiente bloque...")
                continue
                
            logging.info(f"Recibidos {len(flights)} vuelos globales. Filtrando por aeropuertos de la UE...")
            
            # Se construye lista de diccionarios de vuelos filtrados por aeropuertos de la UE
            for flight in flights:
                if flight.estDepartureAirport in eu_aeropuertos:
                    vuelos.append({
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
        # excepcion: si falla un bloque, se registra y se detiene la ejecución para evitar datos incompletos                    
        except Exception as e:
            logging.error(f"Error crítico en el bloque {i+1}: {e}")
            return

    # --- EXPORTACIÓN A CSV ---
    if vuelos:
        df_output = pd.DataFrame(vuelos)
        os.makedirs("data", exist_ok=True)
        output_path = "data/extraccion_etapa1.csv"

        df_output.to_csv(output_path, index=False)
        logging.info(f"Fase Finalizada. Guardados {len(df_output)} vuelos totales de la UE en '{output_path}'.")
    else:
        #CONTROL ERRORES: Si no se extrajo ningún vuelo de la UE
        logging.warning("No se extrajo ningún vuelo coincidente para la lista completa de la UE.")

if __name__ == "__main__":
    extraccion_eu_salidas()