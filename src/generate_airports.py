import pandas as pd

def generate_eu_airports():
    print("📥 Descargando base de datos mundial de aeropuertos desde OurAirports...")
    url = "https://raw.githubusercontent.com/davidmegginson/ourairports-data/master/airports.csv"
    
    df = pd.read_csv(url)
    
    # Países miembros de la UE
    eu_countries = [
        'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 
        'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 
        'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK'
    ]
    
    # Filtro por país y tipo comercial (Grande / Mediano)
    df_eu = df[
        (df['iso_country'].isin(eu_countries)) & 
        (df['type'].isin(['large_airport', 'medium_airport']))
    ]
    
    # 🔥 FILTRO CRÍTICO: Solo códigos ICAO estándar de 4 letras mayúsculas
    df_eu = df_eu[df_eu['ident'].str.match(r'^[A-Z]{4}$', na=False)]
    
    eu_icao_codes = df_eu['ident'].dropna().drop_duplicates().str.strip().tolist()
    
    # Guardamos limpio en la raíz
    pd.DataFrame(eu_icao_codes).to_csv("Eu_airport.csv", index=False, header=False)
    
    print(f"✅ ¡Éxito! Filtrados y guardados {len(eu_icao_codes)} aeropuertos ICAO oficiales de la UE.")
    print("📁 El archivo 'Eu_airport.csv' ha sido depurado con éxito.")

if __name__ == "__main__":
    generate_eu_airports()