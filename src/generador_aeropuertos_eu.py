import pandas as pd

def generador_aeropuertos_eu():
    print("Descargando base de datos mundial de aeropuertos desde OurAirports...")
    url = "https://raw.githubusercontent.com/davidmegginson/ourairports-data/master/airports.csv"
    
    df = pd.read_csv(url)
    
    # Lista para filtrar Países miembros de la UE
    paises_eu = [
        'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 
        'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 
        'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK'
    ]
    
    # Filtro DF por país y tipo  aeropuerto comercial (Grande / Mediano)
    df_eu = df[
        (df['iso_country'].isin(paises_eu)) & 
        (df['type'].isin(['large_airport', 'medium_airport']))
    ]
    
    # Filtro olo códigos ICAO estándar de 4 letras mayúsculas
    df_eu = df_eu[df_eu['ident'].str.match(r'^[A-Z]{4}$', na=False)]
    
    eu_icao_codigos = df_eu['ident'].dropna().drop_duplicates().str.strip().tolist()
    
    # Guardo csv en la raíz
    pd.DataFrame(eu_icao_codigos).to_csv("aeropuertos_eu.csv", index=False, header=False)
    
    print(f"Correcto Filtrados y guardados {len(eu_icao_codigos)} aeropuertos ICAO oficiales de la UE.")
    

if __name__ == "__main__":
    generador_aeropuertos_eu()