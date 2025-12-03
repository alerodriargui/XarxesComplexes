import requests
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import json
import os
from pyvis.network import Network
import numpy as np

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
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            cache = json.load(f)
    else:
        cache = {}

    if address in cache:
        return cache[address]

    url = f"https://mempool.space/api/address/{address}/txs"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        txs = r.json()[:max_tx]
        cache[address] = txs
        with open(DATA_FILE, "w") as f:
            json.dump(cache, f)
        return txs
    except:
        return []

# ======================================================
# 3. Construcción del grafo
# ======================================================
G = nx.DiGraph()

for ex, wallets in EXCHANGES.items():
    for w in wallets:
        G.add_node(w, label=ex, type='exchange')

for ex, wallets in EXCHANGES.items():
    for w in wallets:
        txs = get_transactions(w, max_tx=50)
        for tx in txs:
            for vin in tx.get("vin", []):
                src = vin.get("prevout", {}).get("scriptpubkey_address")
                if src:
                    G.add_node(src, type='user')
                    G.add_edge(src, w, value=vin.get("prevout", {}).get("value", 0)/1e8)
            for vout in tx.get("vout", []):
                dest = vout.get("scriptpubkey_address")
                if dest and dest != w:
                    G.add_node(dest, type='user')
                    G.add_edge(w, dest, value=vout.get("value", 0)/1e8)

print("✅ Grafo construido con transacciones.")

# ======================================================
# 4. Filtrar nodos sin aristas
# ======================================================
nodes_with_edges = [n for n in G.nodes() if G.degree(n) > 0]
G_filtered = G.subgraph(nodes_with_edges).copy()

for n in G_filtered.nodes():
    G_filtered.nodes[n].setdefault('type', 'user')
    G_filtered.nodes[n].setdefault('label', '')

# ======================================================
# 5. Estadísticas generales
# ======================================================
deg = dict(G_filtered.degree())
total_nodes = G_filtered.number_of_nodes()
total_edges = G_filtered.number_of_edges()
num_exchanges = sum(1 for n in G_filtered.nodes() if G_filtered.nodes[n]['label'])
num_users = total_nodes - num_exchanges

components = list(nx.weakly_connected_components(G_filtered))
num_components = len(components)
largest_cc = G_filtered.subgraph(max(components, key=len)).copy()
largest_cc_size = largest_cc.number_of_nodes()
avg_degree = sum(deg.values()) / total_nodes

try:
    diameter = nx.diameter(largest_cc.to_undirected())
except:
    diameter = "No calculable"

# ======================================================
# 6. Detectar nodos puente
# ======================================================
user_to_exchanges = {}
for n in G_filtered.nodes():
    if G_filtered.nodes[n]['label'] == '':
        neighbors = {neigh for neigh in G_filtered.successors(n) if G_filtered.nodes[neigh]['label'] != ''}
        neighbors |= {neigh for neigh in G_filtered.predecessors(n) if G_filtered.nodes[neigh]['label'] != ''}
        user_to_exchanges[n] = len(neighbors)

bridge_nodes = [n for n, c in user_to_exchanges.items() if c >= 2]

# ======================================================
# 7. Flujo BTC y USD
# ======================================================
def get_btc_price_usd():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    resp = requests.get(url)
    return resp.json()['bitcoin']['usd']

btc_price = get_btc_price_usd()

bridge_flows_usd = {}
for n in bridge_nodes:
    in_flow = sum(G_filtered.edges[u, n]['value'] for u in G_filtered.predecessors(n))
    out_flow = sum(G_filtered.edges[n, v]['value'] for v in G_filtered.successors(n))
    total_btc = in_flow + out_flow
    bridge_flows_usd[n] = {
        'in_btc': in_flow,
        'out_btc': out_flow,
        'total_btc': total_btc,
        'total_usd': total_btc * btc_price
    }

top_bridge = max(bridge_flows_usd.items(), key=lambda x: x[1]['total_usd'])[0]

in_exchanges_names = [G_filtered.nodes[u]['label'] for u in G_filtered.predecessors(top_bridge) if G_filtered.nodes[u]['label'] != '']
out_exchanges_names = [G_filtered.nodes[v]['label'] for v in G_filtered.successors(top_bridge) if G_filtered.nodes[v]['label'] != '']

degree_centrality = nx.degree_centrality(G_filtered)
betweenness_centrality = nx.betweenness_centrality(G_filtered)
binance_node = EXCHANGES["Binance"][0]
bridge_node = top_bridge

# ======================================================
# 8. Sección resumen automática (sin duplicar prints)
# ======================================================
section = [
    "=== SECCIÓN AUTOMÁTICA: Propiedades y estructura de la red ===\n",
    f"1. Número de nodos y aristas\n- Total nodos: {total_nodes}\n- Total aristas: {total_edges}\n- Exchanges: {num_exchanges}\n- Usuarios: {num_users}\n",
    f"2. Componentes conectados\n- Componentes débilmente conexas: {num_components}\n- Tamaño del componente gigante: {largest_cc_size}\n",
    f"3. Grado medio: {avg_degree:.4f}\n",
    f"4. Diámetro del componente gigante: {diameter}\n",
    f"5. Nodo puente principal y flujos\n- Nodo puente: {top_bridge}\n- Flujo entrante BTC: {bridge_flows_usd[top_bridge]['in_btc']:.4f}\n- Flujo saliente BTC: {bridge_flows_usd[top_bridge]['out_btc']:.4f}\n- Flujo total BTC: {bridge_flows_usd[top_bridge]['total_btc']:.4f}\n- Flujo total USD: {bridge_flows_usd[top_bridge]['total_usd']:.2f}\n- Exchanges que envían: {in_exchanges_names}\n- Exchanges que reciben: {out_exchanges_names}\n",
    f"6. Centralidad\n- Binance ({binance_node}): Degree {degree_centrality[binance_node]:.4f}, Betweenness {betweenness_centrality[binance_node]:.4f}\n- Nodo puente ({bridge_node}): Degree {degree_centrality[bridge_node]:.4f}, Betweenness {betweenness_centrality[bridge_node]:.4f}\n",
    "=== FIN DE LA SECCIÓN ===\n"
]

print("\n".join(section))

# ======================================================
# 10. Análisis de centralidad
# ======================================================

# Obtener nodos con máxima centralidad
max_degree_node = max(degree_centrality, key=degree_centrality.get)
max_betweenness_node = max(betweenness_centrality, key=betweenness_centrality.get)

# Interpretación individual
print("=== Interpretación individual de centralidad ===")
print(f"1. Degree centrality")
print(f"- Nodo con mayor grado: {max_degree_node} ({degree_centrality[max_degree_node]:.4f})")
print("  Indica el nodo con más conexiones directas; generalmente exchanges activos o nodos puente.")

print(f"\n2. Betweenness centrality")
print(f"- Nodo con mayor betweenness: {max_betweenness_node} ({betweenness_centrality[max_betweenness_node]:.4f})")
print("  Indica el nodo que actúa como intermediario o puente en el flujo de transacciones, esencial para la conectividad de la red.")

# Comparación entre índices
print("\n=== Comparación entre índices ===")
degree_values = np.array(list(degree_centrality.values()))
betweenness_values = np.array(list(betweenness_centrality.values()))
correlation = np.corrcoef(degree_values, betweenness_values)[0, 1]
print(f"- Correlación entre degree y betweenness centrality: {correlation:.4f}")

if max_degree_node == max_betweenness_node:
    print(f"- El nodo con mayor grado coincide con el nodo con mayor betweenness ({max_degree_node}).")
else:
    print(f"- Los nodos máximos difieren: grado -> {max_degree_node}, betweenness -> {max_betweenness_node}.")

print("Interpretación:")
print("- Un valor alto en degree centrality indica nodos muy conectados (exchanges).")
print("- Un valor alto en betweenness centrality indica nodos puente, que controlan el flujo entre grupos.")
print("- La correlación nos dice si los nodos más conectados son también los más importantes como intermediarios.")
print("- En este contexto de red de exchanges y usuarios, es esperable que los nodos puente tengan alto betweenness y nodos centrales de exchanges alto degree.")


# ======================================================
# 11. Visualización interactiva PyVis
# ======================================================
net = Network(height="900px", width="100%", notebook=False, directed=True, bgcolor="#222222", font_color="white")
net.from_nx(G_filtered)

for node in net.nodes:
    node_id = node['id']
    ntype = G_filtered.nodes[node_id]['type']
    if ntype == 'exchange':
        node['color'] = 'red'
        node['size'] = 25
    elif node_id == top_bridge:
        node['color'] = 'orange'
        node['size'] = 35
    else:
        node['color'] = 'blue'
        node['size'] = 10 + np.log(G_filtered.degree(node_id) + 1)

for edge in net.edges:
    edge['width'] = 1 + np.log(edge.get("value", 0.1) + 1)

net.force_atlas_2based(gravity=-50, central_gravity=0.01, spring_length=200, spring_strength=0.05, damping=0.4)
output_file = "btc_exchange_network.html"
net.show(output_file, notebook=False)
print(f"Visualización interactiva guardada como: {output_file} 🚀")

# ======================================================
# 10. Representación estática Matplotlib
# ======================================================
plt.figure(figsize=(25, 20))
pos = nx.spring_layout(G_filtered, k=0.1, iterations=100)
node_color = ['orange' if n == top_bridge else 'red' if G_filtered.nodes[n]['label'] != '' else 'blue' for n in G_filtered.nodes()]
node_size = [20 + deg[n]*10 for n in G_filtered.nodes()]
nx.draw_networkx_nodes(G_filtered, pos, node_size=node_size, node_color=node_color, alpha=0.7)
nx.draw_networkx_edges(G_filtered, pos, alpha=0.2)
labels = {n: G_filtered.nodes[n]['label'] for n in G_filtered.nodes() if G_filtered.nodes[n]['label'] != ''}
nx.draw_networkx_labels(G_filtered, pos, labels, font_size=12, font_color='black')
plt.title("Red BTC: Exchanges (rojo), Puente (naranja), Usuarios (azul)")
plt.axis('off')
plt.show()



# ======================================================
# 12. Distribución de grados
# ======================================================

# Obtener grados de todos los nodos
degrees = [deg[n] for n in G_filtered.nodes()]

# Histograma de distribución de grados
plt.figure(figsize=(10,6))
plt.hist(degrees, bins=range(1, max(degrees)+2), color='skyblue', edgecolor='black', density=True)
plt.title("Distribución de grados de la red BTC")
plt.xlabel("Grado")
plt.ylabel("Frecuencia relativa")
plt.yscale('log')
plt.xscale('log')
plt.grid(True, which="both", ls="--", lw=0.5)
plt.show()

# Ajuste a distribución de potencia usando powerlaw (opcional, si lo tienes instalado)
try:
    import powerlaw
    fit = powerlaw.Fit(degrees, discrete=True)
    alpha = fit.power_law.alpha
    xmin = fit.power_law.xmin
    print(f"\nDistribución de grados ajustada a Power-law:")
    print(f"- Exponente (alpha): {alpha:.4f}")
    print(f"- Grado mínimo considerado (xmin): {xmin}")
    R, p = fit.distribution_compare('power_law', 'exponential')
    if R > 0:
        print("- Mejor ajuste: Power-law frente a exponencial")
    else:
        print("- Mejor ajuste: Exponencial frente a Power-law")
except ModuleNotFoundError:
    print("Instala el paquete 'powerlaw' para ajustar la distribución a un modelo teórico: pip install powerlaw")


# ======================================================
# 13. homophily and assortative mixing
# ======================================================
# Mezcla por tipo de nodo (exchange vs user)
type_assortativity = nx.attribute_assortativity_coefficient(G_filtered, 'type')
print(f"Assortativity por tipo de nodo: {type_assortativity:.4f}")

# Mezcla por grado
degree_assortativity = nx.degree_assortativity_coefficient(G_filtered)
print(f"Assortativity por grado: {degree_assortativity:.4f}")

# Mezcla por betweenness centrality (numérica)
# Convertimos centralidad a atributo numérico para todos los nodos
nx.set_node_attributes(G_filtered, betweenness_centrality, 'betweenness')
betweenness_assortativity = nx.numeric_assortativity_coefficient(G_filtered, 'betweenness')
print(f"Assortativity por betweenness centrality: {betweenness_assortativity:.4f}")
colors = {'exchange':'red', 'user':'blue'}
node_colors = [colors[G_filtered.nodes[n]['type']] for n in G_filtered.nodes()]

plt.figure(figsize=(15,12))
pos = nx.spring_layout(G_filtered, k=0.1, iterations=100)
node_size = [20 + deg[n]*10 for n in G_filtered.nodes()]

nx.draw_networkx_nodes(G_filtered, pos, node_size=node_size, node_color=node_colors, alpha=0.7)
nx.draw_networkx_edges(G_filtered, pos, alpha=0.2)
labels = {n: G_filtered.nodes[n]['label'] for n in G_filtered.nodes() if G_filtered.nodes[n]['label'] != ''}
nx.draw_networkx_labels(G_filtered, pos, labels, font_size=10, font_color='black')

plt.title("Homophily: nodos por tipo (exchange rojo, user azul)")
plt.axis('off')
plt.show()

print("\n=== Interpretación de homophily y assortative mixing ===")
if type_assortativity > 0:
    print(f"- Homophily positiva por tipo de nodo ({type_assortativity:.4f}): nodos similares tienden a conectarse entre sí.")
elif type_assortativity < 0:
    print(f"- Homophily negativa por tipo de nodo ({type_assortativity:.4f}): nodos diferentes se conectan más (disassortative).")
else:
    print(f"- No se observa preferencia por tipo de nodo ({type_assortativity:.4f}).")

if degree_assortativity > 0:
    print(f"- Mezcla assortativa por grado ({degree_assortativity:.4f}): nodos de alto grado conectan con nodos de alto grado.")
else:
    print(f"- Mezcla disassortativa por grado ({degree_assortativity:.4f}): nodos de alto grado conectan con nodos de bajo grado.")

if betweenness_assortativity > 0:
    print(f"- Mezcla assortativa por betweenness ({betweenness_assortativity:.4f}): nodos con alta centralidad actúan juntos.")
else:
    print(f"- Mezcla disassortativa por betweenness ({betweenness_assortativity:.4f}): nodos puente conectan con nodos periféricos.")


