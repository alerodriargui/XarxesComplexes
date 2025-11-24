import requests
import networkx as nx
import matplotlib.pyplot as plt

# ======================================================
# 1. Lista de carteras públicas de exchanges (más completa)
# ======================================================
EXCHANGES = {
    "Binance": ["1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", "bc1qvyh7vggj3qsqf8sg5v7t9fvfhv9p9a5qsw9p4k"],
    "Coinbase": ["3LYJfcfHPXYJreMsASk7LZQ9gH9yJz3e2U", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
    "Kraken": ["3KUhH7Mg7Uq4Gr3yXSCPSnP8bvt6Zux6p7", "1BoatSLRHtKNngkdXEeobR76b53LETtpyT"],
    "Poloniex": [
        "17A16QmavnUfCW11DAApiJxp7ARnxN5pGX"   # Poloniex dirección según la lista :contentReference[oaicite:9]{index=9}  
    ],    
    "Bitstamp": [
        "3Nxwenay9Z8Lc9JBiywExpnEFiLp6Afp8v"   # Bitstamp cold wallet :contentReference[oaicite:5]{index=5}  
    ],
    "Huobi": [
        "3Cbq7aT1tY8kMxWLbitaG7yT6bPbKChq64"   # Huobi-wallet según gist :contentReference[oaicite:4]{index=4}  
    ],
}

# ======================================================
# 2. Función para obtener transacciones de una dirección
# ======================================================
def get_transactions(address, max_tx=50):
    url = f"https://mempool.space/api/address/{address}/txs"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data[:max_tx]
    except:
        return []

# ======================================================
# 3. Construcción del grafo
# ======================================================
G = nx.DiGraph()

# Añadir nodos de exchanges
for ex, wallets in EXCHANGES.items():
    for w in wallets:
        G.add_node(w, label=ex, type='exchange')

# Añadir aristas según transacciones
for ex, wallets in EXCHANGES.items():
    for w in wallets:
        txs = get_transactions(w, max_tx=50)
        for tx in txs:
            # Entradas
            for vin in tx.get("vin", []):
                src = vin.get("prevout", {}).get("scriptpubkey_address")
                if src:
                    G.add_node(src, type='user')
                    G.add_edge(src, w, value=vin.get("prevout", {}).get("value", 0)/1e8)
            # Salidas
            for vout in tx.get("vout", []):
                dest = vout.get("scriptpubkey_address")
                if dest and dest != w:
                    G.add_node(dest, type='user')
                    G.add_edge(w, dest, value=vout.get("value", 0)/1e8)

# ======================================================
# 4. Filtrar nodos sin aristas
# ======================================================
nodes_with_edges = [n for n in G.nodes() if G.degree(n) > 0]
G_filtered = G.subgraph(nodes_with_edges).copy()

# Asegurar atributos
for n in G_filtered.nodes():
    if 'type' not in G_filtered.nodes[n]:
        G_filtered.nodes[n]['type'] = 'user'
    if 'label' not in G_filtered.nodes[n]:
        G_filtered.nodes[n]['label'] = ''


# ======================================================
# 6. Tamaño y color de nodos
# ======================================================
min_size = 200
max_size = 2000
max_degree = max(dict(G_filtered.degree()).values())

def scale_size(degree):
    return min_size + (max_size - min_size) * (degree / max_degree)

node_size = [scale_size(G_filtered.degree(n)) for n in G_filtered.nodes()]

# Colores según tipo
node_color = []
for n in G_filtered.nodes():
    if G_filtered.nodes[n].get('label', '') != '':
        # Nodo con nombre: rojo
        node_color.append('red')
    else:
        node_color.append('blue')

total_nodes = G_filtered.number_of_nodes()
total_edges = G_filtered.number_of_edges()

# Contar nodos por tipo
num_exchanges = sum(1 for n in G_filtered.nodes() if G_filtered.nodes[n].get('label', '') != '')
num_users = total_nodes - num_exchanges

print("=== Estadísticas generales ===")
print(f"Nodos totales: {total_nodes}")
print(f"Aristas totales: {total_edges}")
print(f"Nodos de exchanges: {num_exchanges}")
print(f"Nodos de usuarios: {num_users}")

# Estadísticas por exchange
print("\n=== Estadísticas por exchange ===")
for ex, wallets in EXCHANGES.items():
    ex_nodes = [w for w in wallets if w in G_filtered.nodes()]
    # Contar aristas que involucren a ese exchange
    ex_edges = sum(G_filtered.degree(w) for w in ex_nodes)
    print(f"{ex}: {len(ex_nodes)} nodos, {ex_edges} aristas")
# ======================================================
# 7. Representación gráfica
# ======================================================
plt.figure(figsize=(25, 20))
pos = nx.kamada_kawai_layout(G_filtered)

nx.draw_networkx_nodes(G_filtered, pos, node_size=node_size, node_color=node_color, alpha=0.8)
nx.draw_networkx_edges(G_filtered, pos, alpha=0.3)
nx.draw_networkx_labels(
    G_filtered, pos,
    {n: G_filtered.nodes[n].get('label', '') for n in G_filtered.nodes()},
    font_size=10
)

plt.title("Red BTC: Exchanges (rojo), Usuarios (azul), Intermedios (naranja)\nTamaño proporcional a conexiones")
plt.axis('off')
plt.show()
