# -*- coding: utf-8 -*-
import os
import json
import logging
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from flask import Flask, request, jsonify, send_file

# --- CONFIGURACIÓN ---
# Configuración de logging para ver mejor los errores en la consola
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GRAPH_DIR = "graficos"
os.makedirs(GRAPH_DIR, exist_ok=True)

PALETTE = ['#4285F4', '#EA4335', '#34A853', '#FBBC05']
MEDIOS = ['Medios Digitales', 'Prensa', 'Radio', 'TV']

# --- FUNCIONES UTILITARIAS MEJORADAS ---

def clean_value(value: str | float | int) -> float:
    """
    Convierte un valor a float de forma segura.
    Quita los puntos de miles y maneja posibles errores de conversión.
    """
    if value is None:
        return 0.0
    try:
        # Convierte a string, quita puntos, y luego convierte a float.
        return float(str(value).replace('.', ''))
    except (ValueError, TypeError):
        # Si la conversión falla, retorna 0.0 en lugar de causar un error.
        logging.warning(f"No se pudo convertir el valor '{value}' a número. Se usará 0.0.")
        return 0.0

def _save(fig, filename: str, transparent=False):
    """Función para guardar la figura sin cambios."""
    path = os.path.join(GRAPH_DIR, filename)
    fig.savefig(path, dpi=300, bbox_inches='tight', transparent=transparent)
    plt.close(fig)
    logging.info(f'✅ Gráfico guardado → {path}')

# --- FUNCIONES DE GRÁFICOS (SIN CAMBIOS, YA ERAN ROBUSTAS) ---

def bar_chart(data: dict, title: str, filename: str):
    if not data:
        logging.warning(f"No hay datos para generar el gráfico de barras: {title}")
        return
    # ... (el resto del código de bar_chart no necesita cambios)
    fig, ax = plt.subplots(figsize=(10, 6))
    medios = list(data.keys())
    valores = [v for v in data.values()] # Los valores ya son floats gracias a clean_value
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
    if not data:
        logging.warning(f"No hay datos para generar el gráfico de torta: {title}")
        return
    # ... (el resto del código de pie_chart no necesita cambios)
    fig, ax = plt.subplots(figsize=(6, 6))
    valores = [v for v in data.values()]
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

def top_vpe_por_medio(datos: dict, medio: str):
    # El uso de .get() ya hace esta parte bastante robusta
    noticias = datos.get(f"{medio}_raw", {}).get("noticias", [])
    if not noticias:
        logging.info(f"No se encontraron noticias en '{medio}_raw' para el gráfico Top 10.")
        return
    
    noticias_ordenadas = sorted(noticias, key=lambda x: clean_value(x.get("vpe", 0)), reverse=True)[:10]
    
    if not noticias_ordenadas:
        return # No hay noticias con VPE para graficar
        
    nombres = [n.get('titulo', 'Sin Título') for n in noticias_ordenadas]
    valores = [clean_value(n.get('vpe', 0)) for n in noticias_ordenadas]

    # ... (el resto del código de top_vpe_por_medio no necesita cambios)
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(nombres, valores, color=PALETTE[0])
    ax.set_title(f"Top 10 por VPE - {medio}", fontsize=14, fontweight='bold')
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'.replace(',', '.')))
    for i, b in enumerate(bars):
        ax.text(b.get_width() + max(valores)*0.01, b.get_y() + b.get_height()/2,
                f'{int(valores[i]):,}'.replace(',', '.'), va='center', fontweight='bold')
    plt.tight_layout()
    _save(fig, f"top10_vpe_{medio.lower().replace(' ', '_')}.png")


# --- FLASK APP MEJORADA ---
app = Flask(__name__)

@app.route("/", methods=["POST"])
def generar_graficos():
    try:
        # 1. MANEJO DE FORMATO DE ENTRADA FLEXIBLE
        payload = request.get_json()
        
        if not payload:
            return jsonify({"error": "El cuerpo de la solicitud está vacío o no es JSON válido"}), 400

        datos = {}
        if isinstance(payload, list) and payload:
            # Si es una lista como [{...}], tomamos el primer elemento.
            datos = payload[0]
            logging.info("Payload recibido en formato de Lista, se procesará el primer elemento.")
        elif isinstance(payload, dict):
            # Si ya es un objeto como {...}, lo usamos directamente.
            datos = payload
            logging.info("Payload recibido en formato de Objeto, se procesará directamente.")
        else:
            return jsonify({"error": "El formato del JSON no es ni un objeto ni una lista con un objeto."}), 400

        host_url = request.host_url.rstrip('/')
        graficos_generados = []

        # 2. ACCESO SEGURO A LOS DATOS (EVITA KEYERROR)
        
        # VPE por Medio
        data_vpe = {}
        for medio in MEDIOS:
            # Usamos .get() para evitar errores si un medio no existe o no tiene 'total_vpe'
            medio_data = datos.get(medio, {})
            if "total_vpe" in medio_data:
                data_vpe[medio] = clean_value(medio_data["total_vpe"])

        bar_chart(data_vpe, "VPE por Medio", "vpe_barra.png")
        pie_chart(data_vpe, "Distribución de VPE", "vpe_torta.png")
        graficos_generados += [
            f"{host_url}/grafico/vpe_barra.png",
            f"{host_url}/grafico/vpe_torta.png"
        ]

        # Impactos por Medio
        data_imp = {}
        for medio in MEDIOS:
            medio_data = datos.get(medio, {})
            if "total_audiencia" in medio_data:
                data_imp[medio] = clean_value(medio_data["total_audiencia"])

        bar_chart(data_imp, "Impactos por Medio", "impactos_barra.png")
        pie_chart(data_imp, "Distribución de Impactos", "impactos_torta.png")
        graficos_generados += [
            f"{host_url}/grafico/impactos_barra.png",
            f"{host_url}/grafico/impactos_torta.png"
        ]

        # Top 10 por VPE por Medio
        for medio in MEDIOS:
            top_vpe_por_medio(datos, medio)
            nombre_archivo = f"top10_vpe_{medio.lower().replace(' ', '_')}.png"
            if os.path.exists(os.path.join(GRAPH_DIR, nombre_archivo)):
                graficos_generados.append(f"{host_url}/grafico/{nombre_archivo}")

        return jsonify({
            "status": "ok",
            "archivos_generados": graficos_generados
        })
    # 3. MANEJO DE ERRORES MÁS ESPECiFICO
    except json.JSONDecodeError:
        return jsonify({"error": "El cuerpo de la solicitud no es un JSON válido."}), 400
    except Exception as e:
        logging.error(f"Ha ocurrido un error inesperado: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

# La ruta para servir los gráficos no necesita cambios
@app.route("/grafico/<nombre>")
def servir_grafico(nombre):
    path = os.path.join(GRAPH_DIR, nombre)
    if os.path.exists(path):
        return send_file(path, mimetype="image/png")
    return jsonify({"error": "Archivo no encontrado"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
