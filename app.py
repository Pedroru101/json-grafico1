# -*- coding: utf-8 -*-
import os
import json
import logging
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from flask import Flask, request, jsonify, send_file

# --- CONFIGURACIÓN ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GRAPH_DIR = "graficos"
os.makedirs(GRAPH_DIR, exist_ok=True)

PALETTE = ['#4285F4', '#EA4335', '#34A853', '#FBBC05', '#FF6D00', '#673AB7'] # Paleta extendida por si acaso
MEDIOS = ['Medios Digitales', 'Prensa', 'Radio', 'TV']

# --- FUNCIONES UTILITARIAS (SIN CAMBIOS) ---

def clean_value(value: str | float | int) -> float:
    if value is None:
        return 0.0
    try:
        # Reemplaza comas por puntos para decimales y luego quita los puntos de miles
        cleaned_string = str(value).replace(',', '.')
        # Como los datos de entrada pueden tener '.' como separador de miles, los quitamos antes de convertir
        # Esto asume que no hay decimales importantes después del punto.
        if '.' in cleaned_string:
             # Si el punto está seguido por 3 dígitos y no es el único punto, es probable que sea un separador de miles.
             parts = cleaned_string.split('.')
             if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):
                 cleaned_string = cleaned_string.replace('.', '')

        return float(cleaned_string)
    except (ValueError, TypeError):
        logging.warning(f"No se pudo convertir el valor '{value}' a número. Se usará 0.0.")
        return 0.0

def _save(fig, filename: str, transparent=False):
    path = os.path.join(GRAPH_DIR, filename)
    fig.savefig(path, dpi=300, bbox_inches='tight', transparent=transparent)
    plt.close(fig)
    logging.info(f'✅ Gráfico guardado → {path}')

# --- FUNCIONES DE GRÁFICOS MODIFICADAS ---

def bar_chart(data: dict, title: str, filename: str):
    """
    Función de gráfico de barras (vertical) para VPE/VC/Impactos.
    Ahora coloca el símbolo de euro después del valor.
    """
    if not data:
        logging.warning(f"No hay datos para generar el gráfico de barras: {title}")
        return
    fig, ax = plt.subplots(figsize=(10, 6))
    medios = list(data.keys())
    valores = [v for v in data.values()]
    colors = PALETTE[:len(medios)]
    bars = ax.bar(medios, valores, color=colors)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Medios', fontsize=12)
    # CAMBIO: Etiqueta del eje Y ahora con el símbolo de euro después.
    ax.set_ylabel('Valor', fontsize=12) 
    
    # CAMBIO: Formateador del eje Y para que el euro vaya después.
    # Usamos '{:,.0f} €' para formatear como entero con separador de miles y luego el símbolo de euro.
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,} €'.replace(',', '.'))) 
    
    for b in bars:
        y = b.get_height()
        # CAMBIO: Etiqueta de la barra para que el euro vaya después.
        ax.text(b.get_x() + b.get_width()/2, y * 1.01, f'{int(y):,} €'.replace(',', '.'),
                ha='center', fontweight='bold', va='bottom')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    _save(fig, filename)


def pie_chart(data: dict, title: str, filename: str):
    """
    Función de gráfico de torta modificada para incluir una leyenda detallada
    en la base y mantener los porcentajes dentro de las porciones.
    Ahora coloca el símbolo de euro después del valor en la leyenda.
    """
    if not data or sum(data.values()) == 0:
        logging.warning(f"No hay datos válidos para generar el gráfico de torta: {title}")
        return
        
    fig, ax = plt.subplots(figsize=(8, 7)) 
        
    valores = [v for v in data.values()]
        
    # Se quitan las etiquetas de los medios de dentro de la torta
    wedges, _, autotexts = ax.pie(
        valores,
        colors=PALETTE[:len(data)],
        startangle=90,
        autopct='%1.0f%%', 
        pctdistance=0.85,
        wedgeprops=dict(edgecolor='w', linewidth=2)
    )

    for t in autotexts:
        t.set_color('white')
        t.set_fontweight('bold')
        t.set_fontsize(12)

    ax.set_title(title, weight='bold', fontsize=16, pad=20)

    # NUEVO: Crear etiquetas personalizadas para la leyenda (Medio: Valor €)
    legend_labels = []
    for medio, valor in data.items():
        # CAMBIO: Formato del valor en la leyenda para que el euro vaya después.
        formatted_value = f"{int(valor):,} €".replace(",", ".")
        legend_labels.append(f'{medio}: {formatted_value}')

    # Añadir la leyenda en la base del gráfico
    ax.legend(
        wedges,
        legend_labels,
        title="Leyenda de Valores",
        loc='upper center',
        bbox_to_anchor=(0.5, -0.02), 
        ncol=2, 
        fontsize='medium'
    )

    fig.tight_layout(rect=[0, 0.1, 1, 1]) 
    _save(fig, filename, transparent=True)


def top_vpe_por_medio(datos: dict, medio: str):
    """
    Función de gráfico Top VPE modificada para mejorar la estética:
    - Título corregido
    - Ancho de barras dinámico
    - Posición de etiquetas de valor mejorada
    - Ahora coloca el símbolo de euro después del valor.
    """
    noticias = datos.get(f"{medio}_raw", {}).get("noticias", [])
    if not noticias:
        logging.info(f"No se encontraron noticias en '{medio}_raw' para el gráfico Top.")
        return
        
    noticias_ordenadas = sorted(noticias, key=lambda x: clean_value(x.get("vpe", 0)), reverse=True)[:10]
        
    if not noticias_ordenadas:
        return
        
    nombres = [n.get('titulo', 'Sin Título') for n in noticias_ordenadas]
    valores = [clean_value(n.get('vpe', 0)) for n in noticias_ordenadas]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Ancho (altura en barh) de barra dinámico
    num_bars = len(nombres)
    bar_height = 0.25 if num_bars == 1 else 0.7 

    bars = ax.barh(nombres, valores, color=PALETTE[0], height=bar_height)
        
    # Título del gráfico corregido
    ax.set_title(f"Top VPE - {medio}", fontsize=16, fontweight='bold')
        
    # CAMBIO: Formato de números en el eje X para que el euro vaya después.
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,} €'.replace(',', '.')))

    # Ajustar el límite del eje X para dar espacio a las etiquetas
    if valores:
        max_val = max(valores)
        ax.set_xlim(right=max_val * 1.18) 

    # CAMBIO: Posicionamiento de las etiquetas de valor para evitar desbordamiento
    for bar in bars:
        width = bar.get_width()
        label_x_pos = width + (max_val * 0.01) 
            
        ax.text(
            label_x_pos,
            bar.get_y() + bar.get_height() / 2,
            # CAMBIO: Etiqueta del valor en la barra para que el euro vaya después.
            f'{int(width):,} €'.replace(',', '.'),
            va='center',
            ha='left', 
            fontweight='bold'
        )
        
    # Invertir el eje Y para que la barra más larga quede arriba
    ax.invert_yaxis()

    fig.tight_layout()
    _save(fig, f"top10_vpe_{medio.lower().replace(' ', '_')}.png")


# --- FLASK APP (SIN CAMBIOS) ---
app = Flask(__name__)

@app.route("/", methods=["POST"])
def generar_graficos():
    try:
        payload = request.get_json()
        
        if not payload:
            return jsonify({"error": "El cuerpo de la solicitud está vacío o no es JSON válido"}), 400

        datos = {}
        if isinstance(payload, list) and payload:
            datos = payload[0]
            logging.info("Payload recibido en formato de Lista, se procesará el primer elemento.")
        elif isinstance(payload, dict):
            datos = payload
            logging.info("Payload recibido en formato de Objeto, se procesará directamente.")
        else:
            return jsonify({"error": "El formato del JSON no es ni un objeto ni una lista con un objeto."}), 400

        host_url = request.host_url.rstrip('/')
        graficos_generados = []
        
        # VPE por Medio
        data_vpe = {}
        for medio in MEDIOS:
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
    except json.JSONDecodeError:
        return jsonify({"error": "El cuerpo de la solicitud no es un JSON válido."}), 400
    except Exception as e:
        logging.error(f"Ha ocurrido un error inesperado: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

@app.route("/grafico/<nombre>")
def servir_grafico(nombre):
    path = os.path.join(GRAPH_DIR, nombre)
    if os.path.exists(path):
        return send_file(path, mimetype="image/png")
    return jsonify({"error": "Archivo no encontrado"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
