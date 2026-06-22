import os
import json
import time
import random
import requests
import pandas as pd
from datetime import datetime

# URL oficial de autenticación OAuth2 de OpenSky
TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

def load_api_credentials():
    """Lee el clientId y clientSecret desde tu credentials.json."""
    json_path = "credentials.json"
    if not os.path.exists(json_path):
        print(f"❌ Error: No se encuentra el archivo '{json_path}' en la raíz del proyecto.")
        return None, None
        
    with open(json_path, "r") as file:
        data = json.load(file)
        return data.get("clientId"), data.get("clientSecret")

def get_oauth2_token(client_id, client_secret):
    """Intercambia el clientId y clientSecret por un token Bearer OAuth2 válido."""
    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    except Exception as e:
        print(f"❌ Error al obtener el token OAuth2 desde el servidor de OpenSky: {e}")
        return None

def fetch_real_opensky_data(airport_icao="LEMD"):
    """Se conecta mediante OAuth2 Bearer Token a la API y descarga vuelos reales."""
    client_id, client_secret = load_api_credentials()
    if not client_id or not client_secret:
        print("⚠️ No se pudieron cargar las credenciales (clientId/clientSecret) desde el JSON.")
        return None

    print("🔒 Solicitando token de acceso OAuth2 a los servidores de OpenSky...")
    token = get_oauth2_token(client_id, client_secret)
    if not token:
        print("❌ Autenticación rechazada. No se pudo generar el Token Bearer.")
        return None
        
    print(f"🌐 Autenticando con éxito. Solicitando vuelos de salida de {airport_icao}...")
    
    # Rango de tiempo: últimas 24 horas (Ventana de 6 horas para asegurar registros)
    ahora = int(time.time())
    un_dia = 24 * 60 * 60
    end_time = ahora - un_dia
    begin_time = end_time - (6 * 60 * 60)
    
    url = f"https://opensky-network.org/api/flights/departure?airport={airport_icao}&begin={begin_time}&end={end_time}"
    
    # Pasamos las credenciales modernas en los headers como indica la documentación
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        vuelos_api = response.json()
        
        if not vuelos_api:
            print(f"ℹ️ La API respondió bien, pero no había vuelos registrados en este horario para {airport_icao}.")
            return None
            
        print(f"🚀 ¡Éxito total! Se han descargado {len(vuelos_api)} vuelos REALES usando el nuevo protocolo OAuth2.")
        
        flights_list = []
        for i, f in enumerate(vuelos_api):
            if not f.get("estArrivalAirport"): 
                continue 
                
            first_seen = datetime.fromtimestamp(f["firstSeen"])
            last_seen = datetime.fromtimestamp(f["lastSeen"])
            block_time_hrs = round((f["lastSeen"] - f["firstSeen"]) / 3600, 2)
            
            callsign = f["callsign"].strip() if f.get("callsign") else f"UNK{random.randint(100,999)}"
            ac_reg = f"EC-M{random.choice(['A','B','C','D'])}{i:02d}" 
            unique_id = f"{f['estDepartureAirport']}{f['estArrivalAirport']}{ac_reg}{first_seen.strftime('%Y%m%d%H%M')}"
            
            flights_list.append({
                "Unique ID": unique_id,
                "Serial No": len(flights_list) + 1,
                "Date of operation (UTC)": first_seen.strftime("%d/%m/%Y"),
                "AC registration": ac_reg,
                "Flight ID": callsign,
                "AC type": random.choice(["A320", "B738"]), 
                "Departing Airport ICAO Code": f["estDepartureAirport"],
                "Destination Airport ICAO Code": f["estArrivalAirport"],
                "Departure Time/ Block-off time (UTC)": first_seen.strftime("%H:%M"),
                "Arrival Time/ Block-on Time(UTC)": last_seen.strftime("%H:%M"),
                "Block Time (hrs)": block_time_hrs if block_time_hrs > 0 else 1.5
            })
            
        return pd.DataFrame(flights_list)
        
    except Exception as e:
        print(f"❌ Error al conectar con el endpoint de vuelos: {e}")
        return None

def infer_fuel_properties(df_flights):
    """Motor de Inferencia Aeronáutica: Calcula métricas de combustible estimadas."""
    if df_flights is None or df_flights.empty:
        return pd.DataFrame()
        
    print("🧮 Ejecutando el motor de inferencia matemática para métricas de combustible...")
    BURN_RATE_PER_HOUR = 2.5 
    
    df_flights["Taxi Fuel (tonnes)"] = 0.2
    df_flights["Trip Fuel (tonnes)"] = (df_flights["Block Time (hrs)"] * BURN_RATE_PER_HOUR).round(2)
    df_flights["Contingency Fuel (tonnes)"] = (df_flights["Trip Fuel (tonnes)"] * 0.05).round(2)
    df_flights["Alternate Fuel (tonnes)"] = 0.8
    df_flights["Final Reserve (tonnes)"] = 1.2
    df_flights["Additional Fuel (tonnes)"] = 0.0
    df_flights["Extra Fuel (tonnes)"] = 0.4
    df_flights["Fuel for other safety rules (tonnes)"] = 0.0
    
    df_flights["Aviation Fuel Required (tonnes)"] = (
        df_flights["Taxi Fuel (tonnes)"] + df_flights["Trip Fuel (tonnes)"] + 
        df_flights["Contingency Fuel (tonnes)"] + df_flights["Alternate Fuel (tonnes)"] + 
        df_flights["Final Reserve (tonnes)"]
    ).round(2)
    
    uplift_factors = [1.0, 1.0, 1.0, 1.30, 0.95] 
    df_flights["Actual Aviation Fuel Uplifted (tonnes)"] = (
        df_flights["Aviation Fuel Required (tonnes)"] * [random.choice(uplift_factors) for _ in range(len(df_flights))]
    ).round(2)
    
    JET_A1_DENSITY = 0.8
    df_flights["Density"] = JET_A1_DENSITY
    df_flights["Volume (Litres)"] = ((df_flights["Actual Aviation Fuel Uplifted (tonnes)"] * 1000) / JET_A1_DENSITY).round(0)
    df_flights["Economic tankering category in the flight plan"] = "No"
    df_flights["Block Off (tonnes)"] = (df_flights["Aviation Fuel Required (tonnes)"] + 2.0).round(2)
    df_flights["Block On (tonnes)"] = (df_flights["Block Off (tonnes)"] - df_flights["Trip Fuel (tonnes)"]).round(2)
    df_flights["Previous Flight's Unique ID"] = ""
    df_flights["Supporting documents (as per Art5 guidelines)"] = "Flight log, OFP"
    
    return df_flights

def run_pipeline():
    df_raw = fetch_real_opensky_data("LEMD") 
    
    if df_raw is None or df_raw.empty:
        print("❌ No se pudieron obtener datos reales de la API.")
        return
        
    df_final = infer_fuel_properties(df_raw)
    
    output_path = os.path.join("data", "1_raw", "rawinput.csv")
    df_final.to_csv(output_path, sep=';', decimal=',', index=False)
    
    print(f"\n✨ [FASE E COMPLETA] Archivo '{output_path}' generado con ÉXITO.")
    print(f"📊 Hemos capturado {df_final.shape[0]} vuelos reales de Madrid con consumos inferidos.")

if __name__ == "__main__":
    run_pipeline()