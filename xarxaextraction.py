import requests
import json
import os

# ======================================================
# 1. Lista de carteras públicas de exchanges
# ======================================================
EXCHANGES = {
    "Binance": ["1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", "bc1qvyh7vggj3qsqf8sg5v7t9fvfhv9p9a5qsw9p4k"],
    "Coinbase": ["3LYJfcfHPXYJreMsASk7LZQ9gH9yJz3e2U", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
    "Kraken": ["3KUhH7Mg7Uq4Gr3yXSCPSnP8bvt6Zux6p7", "1BoatSLRHtKNngkdXEeobR76b53LETtpyT"],
    "Poloniex": ["17A16QmavnUfCW11DAApiJxp7ARnxN5pGX"]
}

DATA_FILE = "transactions_cache.json"
MAX_TX = 50  # máximo número de transacciones por wallet

# ======================================================
# 2. Función para descargar transacciones de una wallet
# ======================================================
def download_transactions(address, max_tx=MAX_TX):
    url = f"https://mempool.space/api/address/{address}/txs"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()[:max_tx]
    except Exception as e:
        print(f"Error descargando {address}: {e}")
        return []

# ======================================================
# 3. Descargar todas las transacciones y guardar cache
# ======================================================
def download_all_transactions():
    all_tx = {}
    # Si ya existe cache, cargarla para actualizar solo lo necesario
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            all_tx = json.load(f)

    for exchange, wallets in EXCHANGES.items():
        print(f"\nDescargando transacciones de {exchange}...")
        for wallet in wallets:
            if wallet in all_tx:
                print(f"  {wallet} ya está en cache, saltando...")
                continue
            txs = download_transactions(wallet)
            all_tx[wallet] = txs
            print(f"  {wallet}: {len(txs)} transacciones descargadas")

    # Guardar cache completo
    with open(DATA_FILE, "w") as f:
        json.dump(all_tx, f, indent=2)
    print(f"\n✅ Todas las transacciones guardadas en {DATA_FILE}")

# ======================================================
# 4. Ejecutar
# ======================================================
if __name__ == "__main__":
    download_all_transactions()
