import requests
import pandas as pd

all_data = []
page = 25

while True:
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/tickers?page={page}"
    resp = requests.get(url).json()
    tickers = resp.get('tickers', [])
    
    if not tickers:  # No quedan más tickers
        break
    
    for ticker in tickers:
        all_data.append([
            ticker['market']['name'],
            ticker['base'],
            ticker['target'],
            ticker['last'],
            ticker['volume'],
            ticker['trust_score'],
            ticker['converted_last']['usd']
        ])
    
    print(f"Página {page} procesada, {len(tickers)} tickers")
    page += 1

df = pd.DataFrame(all_data, columns=[
    "Exchange","Base","Target","Last","Volume","Trust Score","USD Price"
])
df.to_csv("btc_markets_all6.csv", index=False)
print(f"¡Datos guardados en btc_markets_all.csv! Total tickers: {len(df)}")
