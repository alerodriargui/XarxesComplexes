import requests
import pandas as pd
import time

# -----------------------------
# Parámetros del mercado
# -----------------------------
MARKET_ID = "robinhood-launches-prediction-market-through-miaxdx-by-march-31"
BASE_URL = "https://data-api.polymarket.com/trades"
LIMIT = 10000  # máximo permitido por request
offset = 0

all_trades = []

# -----------------------------
# Descargar todos los trades
# -----------------------------
while True:
    params = {
        "marketId": MARKET_ID,
        "limit": LIMIT,
        "offset": offset
    }
    response = requests.get(BASE_URL, params=params)
    if response.status_code != 200:
        print("Error en la petición:", response.status_code)
        break

    trades = response.json()
    if not trades:
        break  # no quedan más trades

    all_trades.extend(trades)
    print(f"Descargados {len(trades)} trades (offset {offset})")

    offset += LIMIT
    time.sleep(1)  # para no saturar la API

# -----------------------------
# Guardar a CSV
# -----------------------------
df = pd.DataFrame(all_trades)
csv_file = "polymarket_all_trades.csv"
df.to_csv(csv_file, index=False)
print(f"Guardado en {csv_file}")
print("Número total de trades descargados:", len(all_trades))
