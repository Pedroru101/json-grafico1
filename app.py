# -*- coding: utf-8 -*-
import os
import json
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from flask import Flask, request, jsonify, send_file

# --- CONFIGURACIÓN ---
GRAPH_DIR = "graficos"
os.makedirs(GRAPH_DIR, exist_ok=True)

PALETTE = ['#4285F4', '#EA4335', '#34A853', '#FBBC05']
MEDIOS = ['Medios Digitales', 'Prensa', 'Radio', 'TV']

# --- FUNCIONES UTILITARIAS ---

def clean_value(value: str | float) -> float:
    """Convierte '123.456,78' en 123456.78."""
    return float(str(value).replace('.', '').replace(',', '.'))

def _save(fig, filename: str, transparent=False):
    path = os.path.join(GRAPH_DIR, filename)
    fig.savefig(path, dpi=300, bbox_inches='tight', transparent=transparent)
    plt.close(fig)
    print(f'✅ Gráfico guardado → {path}')

def bar_chart(data: dict, title: str, filename: str):
    fig, ax = plt.subplots(figsize=(10, 6))
    medios = list(data.keys())
    valores = [clean_value(v) for v in data.values()]
    colors = PALETTE[:len(medios)]

    bars = ax.bar(medios, valores, color=colors)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Medios', fontsize=12)
    ax.set_ylabel('Valor (€)', fontsize=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'.replace(',', '.')))

    for b in bars:
        y = b.get_height()
        ax.text(b.get_x() + b.get_width()/2, y * 1.01, f'{int(y):,}'.replace(',', '.'), 
                ha='center', fontweight='bold', va='bottom')

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    _save(fig, filename)

def pie_chart(data: dict, title: str, filename: str):
    fig, ax = plt.subplots(figsize=(6, 6))
    valores = [clean_value(v) for v in data.values()]
    wedges, _, autotexts = ax.pie(
        valores, labels=data.keys(), colors=PALETTE[:len(data)],
        startangle=140, autopct='%1.0f%%', pctdistance=0.85,
        wedgeprops=dict(edgecolor='w')
    )
    for t in autotexts:
        t.set_color('white')
        t.set_fontweight('bold')
    ax.set_title(title, weight='bold')
    _save(fig, filename, transparent=True)

# --- FLASK APP ---
app = Flask(__name__)

@app.route("/", methods=["POST"])
def generar_graficos():
    try:
        payload = request.get_json()
        if not isinstance(payload, list) or not payload:
            return jsonify({"error": "El JSON debe ser una lista con un objeto"}), 400
        
        datos = payload[0]

        # Extraer valores por medio
        data_vpe = {}
        for medio in MEDIOS:
            if medio in datos and 'total_vpe' in datos[medio]:
                data_vpe[medio] = datos[medio]['total_vpe']

        # Validación mínima
        if not data_vpe:
            return jsonify({"error": "No se encontraron datos de VPE válidos"}), 400

        # Generar gráficos
        bar_chart(data_vpe, "VPE por Medio", "vpe_barra.png")
        pie_chart(data_vpe, "Distribución de VPE", "vpe_torta.png")

        return jsonify({
            "status": "ok",
            "archivos_generados": [
                os.path.join(GRAPH_DIR, "vpe_barra.png"),
                os.path.join(GRAPH_DIR, "vpe_torta.png")
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/grafico/<nombre>")
def servir_grafico(nombre):
    path = os.path.join(GRAPH_DIR, nombre)
    if os.path.exists(path):
        return send_file(path, mimetype="image/png")
    return jsonify({"error": "Archivo no encontrado"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
