import os
import pandas as pd

def genera_master_aeropuertos():
    print("📥 Descargando base de datos mundial de aeropuertos desde OurAirports...")
    url = "https://raw.githubusercontent.com/davidmegginson/ourairports-data/master/airports.csv"
    
    try:
        df = pd.read_csv(url)
    except Exception as e:
        print(f"❌ Error al descargar los datos: {e}")
        return
    
    # 1. Filtro por tipo  de aeropuerto comercial Grande y Mediano 
    df_filtered = df[df['type'].isin(['large_airport', 'medium_airport'])].copy()
    
    # 2. Limpieza de códigos: Solo códigos ICAO oficiales de 4 letras mayúsculas
    df_filtered = df_filtered[df_filtered['ident'].str.match(r'^[A-Z]{4}$', na=False)]
    
    # 3. Selecono de las columnas necesarias
    columns_requested = ['id', 'ident', 'name', 'continent', 'iso_country', 'municipality']
    df_master = df_filtered[columns_requested].copy()
    
    # 4.Añado columna identificando los aeupuertos de los paises de la UE(27) para la extracción posterior
    eu_countries = [
        'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 
        'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 
        'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK'
    ]
    df_master['is_ue'] = df_master['iso_country'].isin(eu_countries).astype(int)
    
    # 5. Elimino duplicados si los hubiera en la clave primaria (ident)
    df_master = df_master.dropna(subset=['ident']).drop_duplicates(subset=['ident'])
    
    # 6.Guardo el fichero Maestro Global de aeropuertos 
    output_path = "src/master_aeropuertos.csv"
    df_master.to_csv(output_path, index=False, encoding="utf-8")
    
    print(f"✅ Creado el maestro global con {len(df_master)} aeropuertos comerciales.")
    print(f"📁 Archivo guardado como '{output_path}'")

if __name__ == "__main__":
    genera_master_aeropuertos()