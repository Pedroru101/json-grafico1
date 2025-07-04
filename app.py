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

# --- FUNCIONES UTILITARIAS ---

def clean_value(value: str | float | int) -> float:
    if value is None:
        return 0.0
    try:
        string = str(value).strip()
        if ',' in string and '.' not in string:
            # Valor con coma decimal: "123,45" → "123.45"
            string = string.replace(',', '.')
        elif '.' in string:
            parts = string.split('.')
            if all(len(p) == 3 for p in parts[1:]):  # Ej: 1.234.567
                string = string.replace('.', '')
        return float(string)
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
    if not data or sum(data.values()) == 0: # Añadida verificación para datos vacíos o con suma cero
        logging.warning(f"No hay datos válidos para generar el gráfico de barras: {title}. Archivo: {filename}")
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
    # Se añade un control para valores negativos o flotantes si fuera necesario, aunque para VPE/VC suelen ser enteros positivos.
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
        logging.warning(f"No hay datos válidos para generar el gráfico de torta: {title}. Archivo: {filename}")
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
    - Posición de etiquetas de valor mejorada con estrategia robusta
    - Agrupa noticias por título y suma los VPE para evitar duplicados.
    """
    noticias = datos.get(f"{medio}_raw", {}).get("noticias", [])
    if not noticias:
        logging.info(f"No se encontraron noticias en '{medio}_raw' para el gráfico Top VPE de {medio}.")
        return

    # Agrupar noticias por título y sumar los VPE
    vpe_por_titulo = {}
    for n in noticias:
        titulo = n.get('titulo', 'Sin Título')
        vpe = clean_value(n.get('vpe', 0))
        vpe_por_titulo[titulo] = vpe_por_titulo.get(titulo, 0) + vpe

    # Ordenar por VPE descendente y tomar los top 10
    noticias_ordenadas = sorted(vpe_por_titulo.items(), key=lambda x: x[1], reverse=True)[:10]
    if not noticias_ordenadas:
        logging.info(f"No hay noticias con VPE válido para el gráfico Top VPE de {medio}.")
        return

    nombres = [t for t, _ in noticias_ordenadas]
    valores = [v for _, v in noticias_ordenadas]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Ancho (altura en barh) de barra dinámico
    num_bars = len(nombres)
    bar_height = 0.25 if num_bars == 1 else 0.7

    bars = ax.barh(nombres, valores, color=PALETTE[0], height=bar_height)

    # Título del gráfico corregido
    ax.set_title(f"Top VPE - {medio}", fontsize=16, fontweight='bold')

    # Formato de números en el eje X para que el euro vaya después
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,} €'.replace(',', '.')))

    # Ajustar el límite del eje X para dar espacio a las etiquetas
    if valores:
        max_val = max(valores)
        if max_val == 0:
            ax.set_xlim(right=1)  # Establecer un límite mínimo si todos los valores son 0
        else:
            ax.set_xlim(right=max_val * 1.25)  # Aumentar espacio para etiquetas

    # Nueva estrategia de posicionamiento de etiquetas
    for bar in bars:
        width = bar.get_width()
        min_offset = 0.05 * ax.get_xlim()[1]  # 5% del límite del eje X como mínimo
        dynamic_offset = 0.02 * max_val if max_val != 0 else min_offset  # 2% del valor máximo o mínimo
        label_x_pos = width + max(min_offset, dynamic_offset)  # Usar el mayor entre ambos

        ax.text(
            label_x_pos,
            bar.get_y() + bar.get_height() / 2,
            f'{int(width):,} €'.replace(',', '.'),
            va='center',
            ha='left',
            fontweight='bold'
        )

    # Invertir el eje Y para que la barra más larga quede arriba
    ax.invert_yaxis()

    fig.tight_layout()
    _save(fig, f"top10_vpe_{medio.lower().replace(' ', '_')}.png")
# --- FLASK APP ---
app = Flask(__name__)

@app.route("/", methods=["POST"])
def generar_graficos():
    try:
        payload = request.get_json()

        if not payload:
            return jsonify({"error": "El cuerpo de la solicitud está vacío o no es JSON válido"}), 400

        datos = {}
        # Asumiendo que el payload es una lista de un solo diccionario
        # o directamente un diccionario.
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
            else:
                logging.warning(f"No se encontró 'total_vpe' para el medio '{medio}' en el nivel superior. Se omitirá para VPE.")


        bar_chart(data_vpe, "VPE por Medio", "vpe_barra.png")
        pie_chart(data_vpe, "Distribución de VPE", "vpe_torta.png")
        if data_vpe: # Solo añadir si se generaron los gráficos
            graficos_generados += [
                f"{host_url}/grafico/vpe_barra.png",
                f"{host_url}/grafico/vpe_torta.png"
            ]

        # Impactos por Medio (CORRECCIÓN APLICADA AQUÍ)
        data_imp = {}
        for medio in MEDIOS:
            raw_medio_data = datos.get(f"{medio}_raw", {}) # Accede a la clave "TV_raw", "Radio_raw", etc.
            if "total_vc" in raw_medio_data: # Ahora busca 'total_vc'
                data_imp[medio] = clean_value(raw_medio_data["total_vc"])
            else:
                logging.warning(f"No se encontró 'total_vc' para el medio '{medio}' en '{medio}_raw'. Se omitirá para Impactos.")

        bar_chart(data_imp, "Impactos por Medio", "impactos_barra.png")
        pie_chart(data_imp, "Distribución de Impactos", "impactos_torta.png")
        if data_imp: # Solo añadir si se generaron los gráficos
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
