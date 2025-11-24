import pandas as pd
import glob

# Ruta de los archivos CSV (ajusta si están en otra carpeta)
file_pattern = "btc_markets_all*.csv"

# Encuentra todos los CSV que coincidan con el patrón
files = sorted(glob.glob(file_pattern))

# Lista para guardar los DataFrames
dfs = []

for f in files:
    df = pd.read_csv(f)
    dfs.append(df)
    print(f"{f} cargado, {len(df)} filas")

# Concatenar todos los DataFrames
combined_df = pd.concat(dfs, ignore_index=True)

# Opcional: eliminar filas duplicadas
combined_df.drop_duplicates(subset=["Exchange","Base","Target","Last"], inplace=True)

# Guardar en un nuevo CSV
combined_df.to_csv("btc_markets_combined.csv", index=False)
print(f"¡Todos los archivos combinados! Total filas: {len(combined_df)}")
