import requests
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
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


# ======================================================
# 2. Función para obtener transacciones (con cache)
# ======================================================
def get_transactions(address, max_tx=50):
    # Cargar cache si existe
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            cache = json.load(f)
    else:
        cache = {}

    if address in cache:
        return cache[address]

    # Si no está en cache, descargar
    url = f"https://mempool.space/api/address/{address}/txs"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        txs = r.json()[:max_tx]
        cache[address] = txs
        # Guardar cache actualizado
        with open(DATA_FILE, "w") as f:
            json.dump(cache, f)
        return txs
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

print("Transacciones cargadas y grafo construido ✅")

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
# 5. Estadísticas generales
# ======================================================
deg = dict(G_filtered.degree())
total_nodes = G_filtered.number_of_nodes()
total_edges = G_filtered.number_of_edges()
num_exchanges = sum(1 for n in G_filtered.nodes() if G_filtered.nodes[n].get('label', '') != '')
num_users = total_nodes - num_exchanges

print("=== Estadísticas generales ===")
print(f"Nodos totales: {total_nodes}")
print(f"Aristas totales: {total_edges}")
print(f"Nodos de exchanges: {num_exchanges}")
print(f"Nodos de usuarios: {num_users}")

print("\n=== Estadísticas por exchange ===")
for ex, wallets in EXCHANGES.items():
    ex_nodes = [w for w in wallets if w in G_filtered.nodes()]
    ex_edges = sum(G_filtered.degree(w) for w in ex_nodes)
    print(f"{ex}: {len(ex_nodes)} nodos, {ex_edges} aristas")

# Componentes
components = list(nx.weakly_connected_components(G_filtered))
num_components = len(components)
largest_cc = G_filtered.subgraph(max(components, key=len)).copy()
largest_cc_size = largest_cc.number_of_nodes()
avg_degree = sum(deg.values()) / total_nodes

try:
    diameter = nx.diameter(largest_cc.to_undirected())
except:
    diameter = "No calculable"

print("\n=== Propiedades estructurales ===")
print("Componentes conexas:", num_components)
print("Tamaño del componente gigante:", largest_cc_size)
print("Grado medio:", avg_degree)
print("Diámetro:", diameter)

# ======================================================
# 6. Detectar nodos puente
# ======================================================
user_to_exchanges = {}
for n in G_filtered.nodes():
    if G_filtered.nodes[n].get('label', '') == '':
        neighbors = set()
        for neigh in G_filtered.successors(n):
            if G_filtered.nodes[neigh].get('label', '') != '':
                neighbors.add(neigh)
        for neigh in G_filtered.predecessors(n):
            if G_filtered.nodes[neigh].get('label', '') != '':
                neighbors.add(neigh)
        user_to_exchanges[n] = len(neighbors)

bridge_nodes = [n for n, c in user_to_exchanges.items() if c >= 2]

# ======================================================
# 7. Calcular flujo de BTC y USD
# ======================================================
def get_btc_price_usd():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    resp = requests.get(url)
    data = resp.json()
    return data['bitcoin']['usd']

btc_price = get_btc_price_usd()

bridge_flows_usd = {}
for n in bridge_nodes:
    in_flow = sum(G_filtered.edges[u, n]['value'] for u in G_filtered.predecessors(n))
    out_flow = sum(G_filtered.edges[n, v]['value'] for v in G_filtered.successors(n))
    total_btc = in_flow + out_flow
    total_usd = total_btc * btc_price
    bridge_flows_usd[n] = {
        'in_btc': in_flow,
        'out_btc': out_flow,
        'total_btc': total_btc,
        'total_usd': total_usd
    }

# Top 5 nodos puente por flujo USD
top_bridge = max(bridge_flows_usd.items(), key=lambda x: x[1]['total_usd'])[0]
print(f"\nNodo puente principal: {top_bridge}")
print(f"Flujo total BTC: {bridge_flows_usd[top_bridge]['total_btc']:.4f} BTC")
print(f"Valor estimado USD: ${bridge_flows_usd[top_bridge]['total_usd']:.2f}")

# Exchanges y usuarios conectados al puente
in_neighbors = [u for u in G_filtered.predecessors(top_bridge)]
out_neighbors = [v for v in G_filtered.successors(top_bridge)]
in_exchanges = [u for u in in_neighbors if G_filtered.nodes[u].get('label', '') != '']
out_exchanges = [v for v in out_neighbors if G_filtered.nodes[v].get('label', '') != '']
in_exchanges_names = [G_filtered.nodes[u]['label'] for u in in_neighbors if G_filtered.nodes[u].get('label', '') != '']
out_exchanges_names = [G_filtered.nodes[v]['label'] for v in out_neighbors if G_filtered.nodes[v].get('label', '') != '']
print("Entradas desde exchanges:", in_exchanges_names)
print("Salidas hacia exchanges:", out_exchanges_names)


# Degree centrality
degree_centrality = nx.degree_centrality(G_filtered)

# Betweenness centrality
betweenness_centrality = nx.betweenness_centrality(G_filtered)

# Nodo Binance más representativo (primera wallet)
binance_node = EXCHANGES["Binance"][0]
bridge_node = top_bridge

print(f"=== Centralidad Binance ({binance_node}) ===")
print(f"Degree centrality: {degree_centrality[binance_node]:.4f}")
print(f"Betweenness centrality: {betweenness_centrality[binance_node]:.4f}")

print(f"\n=== Centralidad Nodo Puente ({bridge_node}) ===")
print(f"Degree centrality: {degree_centrality[bridge_node]:.4f}")
print(f"Betweenness centrality: {betweenness_centrality[bridge_node]:.4f}")

# ======================================================
# 8. Representación gráfica
# ======================================================
plt.figure(figsize=(25, 20))
pos = nx.spring_layout(G_filtered, k=0.1, iterations=100)

# Colores: exchanges rojo, puentes naranja, usuarios azul
node_color = []
for n in G_filtered.nodes():
    if n == top_bridge:
        node_color.append('orange')
    elif G_filtered.nodes[n].get('label', '') != '':
        node_color.append('red')
    else:
        node_color.append('blue')

node_size = [20 + deg[n]*10 for n in G_filtered.nodes()]

nx.draw_networkx_nodes(G_filtered, pos, node_size=node_size, node_color=node_color, alpha=0.7)
nx.draw_networkx_edges(G_filtered, pos, alpha=0.2)

# Labels solo para exchanges
labels = {n: G_filtered.nodes[n].get('label', '') for n in G_filtered.nodes() if G_filtered.nodes[n].get('label', '') != ''}
nx.draw_networkx_labels(G_filtered, pos, labels, font_size=12, font_color='black')

plt.title("Red BTC: Exchanges (rojo), Puente principal (naranja), Usuarios (azul)")
plt.axis('off')
plt.show()
