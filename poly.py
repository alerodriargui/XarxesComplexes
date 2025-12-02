import requests
import pandas as pd
import networkx as nx
from pyvis.network import Network
import numpy as np

MARKET_ID = "will-robinhood-launch-stock-tokens-in-the-us-before-2026"
BASE_URL = "https://data-api.polymarket.com"

# Obtener trades
url = f"{BASE_URL}/trades?marketId={MARKET_ID}&limit=10000"
response = requests.get(url)
trades_data = response.json()

# Convertir a DataFrame
df = pd.DataFrame(trades_data)
df = df[['proxyWallet', 'side', 'asset', 'conditionId', 'size', 'price', 'timestamp', 'outcome', 'pseudonym', 'transactionHash']]
print(df.head())

# Agrupar trades por usuario
# --------------------------
df_grouped = df.groupby(['proxyWallet', 'side']).agg({'size':'sum'}).reset_index()

# --------------------------
# Construir grafo dirigido
# --------------------------
G = nx.DiGraph()
MARKET_NODE = "Market"

for _, row in df_grouped.iterrows():
    user = row['proxyWallet']
    size = row['size']
    
    if row['side'] == "BUY":
        G.add_edge(user, MARKET_NODE, weight=size)
    elif row['side'] == "SELL":
        G.add_edge(MARKET_NODE, user, weight=size)

print("Número de nodos:", G.number_of_nodes())
print("Número de aristas:", G.number_of_edges())
print("Grados promedio:", sum(dict(G.degree()).values()) / G.number_of_nodes())
print("Es conexa?", nx.is_weakly_connected(G))

# --------------------------
# Análisis de la red
# --------------------------
print("=== Estadísticas de la red ===")
print("Número de nodos:", G.number_of_nodes())
print("Número de aristas:", G.number_of_edges())
print("Grado promedio:", sum(dict(G.degree()).values()) / G.number_of_nodes())
print("Es conexa?", nx.is_weakly_connected(G))

# Nodo con mayor grado
degree_dict = dict(G.degree())
max_degree_node = max(degree_dict, key=degree_dict.get)
print("Nodo con mayor grado:", max_degree_node, "Grado:", degree_dict[max_degree_node])

# Nodo con mayor grado ponderado (peso de aristas)
weighted_degree = dict(G.degree(weight='weight'))
max_weight_node = max(weighted_degree, key=weighted_degree.get)
print("Nodo con mayor grado ponderado:", max_weight_node, "Peso total de trades:", weighted_degree[max_weight_node])

# Centralidad de intermediación (betweenness)
betweenness = nx.betweenness_centrality(G, weight='weight')
max_bc_node = max(betweenness, key=betweenness.get)
print("Nodo con mayor centralidad (betweenness):", max_bc_node, "Centralidad:", betweenness[max_bc_node])

# Suma total de flujo hacia/desde el Market (¿suma 0?)
inflow = sum([d['weight'] for u,v,d in G.in_edges(MARKET_NODE, data=True)])
outflow = sum([d['weight'] for u,v,d in G.out_edges(MARKET_NODE, data=True)])
print("Flujo total hacia Market:", inflow)
print("Flujo total desde Market:", outflow)
print("Flujo neto (in - out):", inflow - outflow)

total_volume = df['size'].sum()
print("Volumen total del market:", total_volume)

df_active = df[df['outcome'].isna()]   # trades aún activos
df_past   = df[df['outcome'].notna()]  # trades ya resueltos

print("Número de trades activos:", len(df_active))
print("Número de trades pasados:", len(df_past))

vol_active = df_active['size'].sum()
vol_past   = df_past['size'].sum()
print("Volumen de trades activos:", vol_active)
print("Volumen de trades pasados:", vol_past)
# Usuarios más activos
top_users = sorted(weighted_degree.items(), key=lambda x: x[1], reverse=True)
print("\nTop 5 usuarios por volumen total:")
for u, w in top_users[:5]:
    if u != MARKET_NODE:
        print(u, "→ Volumen total:", w)

# --------------------------
# Visualización interactiva
# --------------------------
net = Network(height="800px", width="100%", notebook=True, directed=True, bgcolor="#222222", font_color="white")
net.from_nx(G)

for node in net.nodes:
    if node['id'] == MARKET_NODE:
        node['color'] = 'red'
        node['size'] = 30
        node['fixed'] = True
    else:
        node['color'] = 'blue'
        node['size'] = 10 + np.log(G.degree(node['id']) + 1)

for edge in net.edges:
    weight = edge.get('weight', 1)
    edge['width'] = 1 + np.log(weight + 1)

# Física para expandir la red
net.force_atlas_2based(gravity=-50, central_gravity=0.01, spring_length=200, spring_strength=0.05, damping=0.4)

# Guardar HTML interactivo
net.show("polymarket_network.html")