import os
import re
import json
import csv

import pandas as pd
from playwright.sync_api import sync_playwright

URL = "https://visorsisben.sdp.gov.co/"

SELECTOR_EDAD = '[data-testid="stElementContainer"].st-key-edad'
SELECTOR_LOCALIDAD = '[data-testid="stElementContainer"].st-key-localidad_seleccionada'
SELECTOR_SECTOR = '[data-testid="stElementContainer"].st-key-sector_catastral'
SELECTOR_GRID = "div.stDataFrameGlideDataEditor"
SELECTOR_BOTON_DESCARGA = 'button[aria-label="Download as CSV"]'
from pathlib import Path

# ============================================================
# RUTA BASE DEL PROYECTO
# ============================================================

# .../EntregablesDiego/CodigosdeAnalisisLimpiezasyFormato/tu_scrapper.py
CARPETA_CODIGOS = Path(__file__).resolve().parent

# .../EntregablesDiego
CARPETA_PROYECTO = CARPETA_CODIGOS.parent

# ============================================================
# CARPETAS DE DATOS
# ============================================================

CARPETA_DESCARGADOS = CARPETA_PROYECTO / "CSVUsados" / "Descargados"

CARPETA_SALIDA = (
    CARPETA_PROYECTO
    / "CSVUsados"
    / "Generados"
    / "PoblacionMayor"
)

# Crear carpetas si no existen
CARPETA_DESCARGADOS.mkdir(parents=True, exist_ok=True)
CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)

# ============================================================
# ARCHIVOS DE SALIDA
# ============================================================

ARCHIVO_SALIDA_JSON = (
    CARPETA_SALIDA / "personas_Mayores_por_barrio.json"
)

ARCHIVO_SALIDA_CSV = (
    CARPETA_SALIDA / "personas_Mayores_por_barrio_resumen.csv"
)

# Reintentos cuando el grid todavía no terminó de re-renderizar y el
# CSV descargado sale vacío.
MAX_REINTENTOS_DESCARGA = 4
ESPERA_BASE_MS = 900  # se multiplica por el número de intento (900, 1800, 2700, 3600)

# -----------------------------------------------------------------
# El sitio usa la File System Access API (window.showSaveFilePicker)
# para el botón "Download as CSV", que abre un selector nativo del
# sistema operativo y no tiene fallback a una descarga clásica. La
# reemplazamos por una versión falsa (ver JS_PICKER_FALSO más abajo)
# que, en vez de mostrar un diálogo, captura el contenido escrito y
# lo entrega acá mediante context.expose_function. Este diccionario
# es el "buzón" donde queda ese contenido; se resetea antes de cada
# descarga.
# -----------------------------------------------------------------
_contenido_csv_capturado = {"valor": None}


def _recibir_csv_desde_pagina(contenido):
    """
    Callback expuesto a la página como window.__enviarContenidoCSV.
    El picker falso lo invoca con el texto completo del CSV cuando
    la página "cierra" el archivo (createWritable().close()).
    """
    _contenido_csv_capturado["valor"] = contenido


JS_PICKER_FALSO = r"""
(() => {
    function bufferToText(buffer) {
        const arr = buffer instanceof ArrayBuffer ? buffer : buffer.buffer;
        return new TextDecoder().decode(arr);
    }

    async function agregarParte(dato, partes) {
        if (dato === null || dato === undefined) return;

        // Formato WriteParams: { type: 'write', data, position } (u otros
        // tipos como 'seek'/'truncate', que ignoramos).
        if (
            typeof dato === 'object' &&
            !(dato instanceof Blob) &&
            !(dato instanceof ArrayBuffer) &&
            !ArrayBuffer.isView(dato) &&
            'data' in dato
        ) {
            if (dato.type && dato.type !== 'write') {
                return;
            }
            await agregarParte(dato.data, partes);
            return;
        }

        if (dato instanceof Blob) {
            partes.push(await dato.text());
        } else if (dato instanceof ArrayBuffer || ArrayBuffer.isView(dato)) {
            partes.push(bufferToText(dato));
        } else if (typeof dato === 'string') {
            partes.push(dato);
        }
    }

    Object.defineProperty(window, 'showSaveFilePicker', {
        configurable: true,
        value: async function (opciones) {
            const partes = [];
            return {
                kind: 'file',
                name: (opciones && opciones.suggestedName) || 'descarga.csv',
                createWritable: async function () {
                    return {
                        write: async function (dato) {
                            await agregarParte(dato, partes);
                        },
                        close: async function () {
                            const contenidoFinal = partes.join('');
                            if (window.__enviarContenidoCSV) {
                                await window.__enviarContenidoCSV(contenidoFinal);
                            }
                        },
                        abort: async function () {},
                    };
                },
            };
        },
    });
})();
"""


def sanitizar_nombre(texto):
    """Convierte un nombre de localidad/barrio en algo seguro para usar como nombre de archivo."""
    texto = texto.strip()
    texto = re.sub(r"[^\w\-]+", "_", texto)
    return texto.strip("_")


# ===========================================================
# Funciones reutilizables para comboboxes de Streamlit
# ===========================================================

def abrir_selector(page, selector_contenedor):
    """
    Hace clic en el combobox dentro de `selector_contenedor` para abrir
    su desplegable, y devuelve el locator del <ul> con las opciones.
    """
    contenedor = page.locator(selector_contenedor)
    combo = contenedor.locator('[role="combobox"]')

    if combo.count() == 0:
        raise RuntimeError(
            f"No se encontró ningún combobox dentro de: {selector_contenedor}"
        )

    combo.click()
    page.wait_for_timeout(400)

    dropdown = page.locator('ul[data-testid="stSelectboxVirtualDropdown"]')
    dropdown.wait_for(state="visible", timeout=5000)
    return dropdown


def listar_opciones(page, dropdown, max_intentos=100):
    """
    Recolecta TODAS las opciones de un dropdown virtualizado,
    scrolleando con la rueda del mouse (evento real) hasta que dejen
    de aparecer opciones nuevas. Devuelve la lista de textos en el
    orden en que fueron apareciendo.
    """
    caja = dropdown.bounding_box()
    if caja is None:
        raise RuntimeError("No se pudo obtener la posición del desplegable.")

    centro_x = caja["x"] + caja["width"] / 2
    centro_y = caja["y"] + caja["height"] / 2
    page.mouse.move(centro_x, centro_y)

    vistas = {}
    intentos_sin_novedad = 0

    for _ in range(max_intentos):
        opciones = dropdown.locator('li[role="option"]')
        nuevas = 0
        for i in range(opciones.count()):
            try:
                texto = opciones.nth(i).inner_text().strip()
            except Exception:
                continue
            if texto and texto not in vistas:
                vistas[texto] = True
                nuevas += 1

        if nuevas == 0:
            intentos_sin_novedad += 1
        else:
            intentos_sin_novedad = 0

        if intentos_sin_novedad >= 4:
            break

        page.mouse.wheel(0, 250)
        page.wait_for_timeout(200)

    return list(vistas.keys())


def seleccionar_opcion(page, dropdown, texto_opcion, max_intentos=150, exacto=False):
    """
    Busca una opción dentro de un dropdown virtualizado, scrolleando
    con la rueda del mouse si hace falta hasta encontrarla, y hace
    clic sobre ella.

    - exacto=False (default): coincide si `texto_opcion` está CONTENIDO
      en el texto de la opción.
    - exacto=True: coincide solo si el texto es exactamente igual.

    Devuelve True si la encontró y le hizo clic, False si no apareció
    tras recorrer toda la lista.
    """
    caja = dropdown.bounding_box()
    if caja is None:
        raise RuntimeError("No se pudo obtener la posición del desplegable.")

    centro_x = caja["x"] + caja["width"] / 2
    centro_y = caja["y"] + caja["height"] / 2
    page.mouse.move(centro_x, centro_y)

    objetivo = texto_opcion.strip().lower()

    for _ in range(max_intentos):
        opciones = dropdown.locator('li[role="option"]')
        for i in range(opciones.count()):
            try:
                texto = opciones.nth(i).inner_text().strip()
            except Exception:
                continue

            texto_normalizado = texto.lower()
            coincide = (
                texto_normalizado == objetivo
                if exacto
                else objetivo in texto_normalizado
            )
            if coincide:
                opciones.nth(i).click()
                return True

        page.mouse.wheel(0, 250)
        page.wait_for_timeout(200)

    return False


# ===========================================================
# Descarga del CSV y lectura del valor (última fila, última columna)
# ===========================================================

def descargar_csv(page, nombre_archivo, tiempo_max_ms=6000, paso_ms=150):
    """
    Hace clic en "Download as CSV". Como el sitio usa
    window.showSaveFilePicker (reemplazado por nuestra versión falsa,
    ver JS_PICKER_FALSO), no aparece ningún diálogo: el contenido
    queda en _contenido_csv_capturado vía _recibir_csv_desde_pagina.
    Esta función espera a que llegue, lo guarda en
    CARPETA_DESCARGAS/nombre_archivo y devuelve la ruta.
    """
    os.makedirs(CARPETA_DESCARGAS, exist_ok=True)
    _contenido_csv_capturado["valor"] = None

    grid = page.locator(SELECTOR_GRID).first
    grid.wait_for(state="visible", timeout=5000)
    grid.hover()
    page.wait_for_timeout(200)

    boton = page.locator(SELECTOR_BOTON_DESCARGA).first
    boton.wait_for(state="visible", timeout=5000)
    boton.click()

    transcurrido = 0
    while _contenido_csv_capturado["valor"] is None and transcurrido < tiempo_max_ms:
        page.wait_for_timeout(paso_ms)
        transcurrido += paso_ms

    if _contenido_csv_capturado["valor"] is None:
        raise TimeoutError(
            "No se recibió contenido del CSV (el showSaveFilePicker falso "
            "no fue invocado; puede que el sitio haya cambiado de mecanismo "
            "de descarga)."
        )

    contenido = _contenido_csv_capturado["valor"]
    ruta = os.path.join(CARPETA_DESCARGAS, nombre_archivo)
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        f.write(contenido)

    return ruta


def csv_tiene_contenido(ruta_csv):
    """
    True si el archivo existe y tiene al menos una línea no vacía.
    Se usa para detectar descargas hechas antes de que el grid
    terminara de re-renderizar (CSV vacío).
    """
    try:
        with open(ruta_csv, "r", encoding="utf-8-sig", newline="") as f:
            contenido = f.read()
    except OSError:
        return False
    return any(linea.strip() != "" for linea in contenido.splitlines())


def extraer_valor_desde_csv(ruta_csv):
    """
    Devuelve el valor de la última fila / última columna del CSV
    (la celda inferior derecha del grid, confirmada como la que trae
    el número total de personas).

    No usa el "sniffer" de pandas (sep=None) porque falla con
    "Could not determine delimiter" cuando el CSV descargado tiene
    una sola columna (no hay ningún delimitador que detectar, algo
    que pasa seguido cuando la tabla filtrada queda con un solo
    valor). En su lugar, se lee la última línea manualmente: si
    contiene un delimitador conocido se parte por ahí, y si no, se
    toma la línea completa como el valor único.
    """
    with open(ruta_csv, "r", encoding="utf-8-sig", newline="") as f:
        contenido = f.read()

    lineas = [linea for linea in contenido.splitlines() if linea.strip() != ""]
    if not lineas:
        raise ValueError(f"El archivo '{ruta_csv}' está vacío.")

    ultima_linea = lineas[-1]

    delimitador = None
    for candidato in [",", ";", "\t", "|"]:
        if candidato in ultima_linea:
            delimitador = candidato
            break

    if delimitador is None:
        # No hay delimitador: la última fila tiene un solo campo.
        valor = ultima_linea
    else:
        campos = next(csv.reader([ultima_linea], delimiter=delimitador))
        valor = campos[-1]

    return valor.strip().strip('"').strip()


def construir_tabla_final(resultados):
    """
    Aplana el diccionario {localidad: {barrio: valor}} en una tabla
    con columnas: localidad, barrio, total_personas_mayores.
    Intenta convertir el total a número (limpiando separadores de
    miles); si no se puede, deja NaN en la columna numérica pero
    conserva el valor original en total_personas_mayores_raw.
    """
    filas = []
    for localidad, barrios_dict in resultados.items():
        for barrio, valor in barrios_dict.items():
            filas.append(
                {
                    "localidad": localidad,
                    "barrio": barrio,
                    "total_personas_mayores_raw": valor,
                }
            )

    tabla = pd.DataFrame(
        filas, columns=["localidad", "barrio", "total_personas_mayores_raw"]
    )

    valores_limpios = (
        tabla["total_personas_mayores_raw"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    tabla["total_personas_mayores"] = pd.to_numeric(valores_limpios, errors="coerce")

    columnas_finales = [
        "localidad",
        "barrio",
        "total_personas_mayores",
        "total_personas_mayores_raw",
    ]
    return tabla[columnas_finales]


# ===========================================================
# Flujo principal
# ===========================================================

with sync_playwright() as p:

    browser = p.chromium.launch(headless=False)
    context = browser.new_context(accept_downloads=True)

    # -----------------------------------------------------------
    # El sitio usa la File System Access API
    # (window.showSaveFilePicker) para el botón "Download as CSV",
    # y no tiene fallback a una descarga clásica del navegador (ya
    # lo confirmamos: al esconder la función, el botón dejaba de
    # funcionar). En vez de esconderla, la reemplazamos por
    # JS_PICKER_FALSO, que finge ser el selector nativo pero en
    # realidad captura el contenido escrito y lo entrega acá vía
    # context.expose_function -> _recibir_csv_desde_pagina. Nunca
    # aparece ningún diálogo.
    # -----------------------------------------------------------
    context.expose_function("__enviarContenidoCSV", _recibir_csv_desde_pagina)
    context.add_init_script(JS_PICKER_FALSO)

    page = context.new_page()

    page.goto(URL, wait_until="networkidle", timeout=60000)
    print("Página cargada.")

    # -----------------------------------------------------------
    # 1) Seleccionar "Adultos mayores (60+)" en el filtro de edad
    # -----------------------------------------------------------
    dropdown_edad = abrir_selector(page, SELECTOR_EDAD)
    ok = seleccionar_opcion(page, dropdown_edad, "Adultos mayores")
    print("¿Se seleccionó 'Adultos mayores (60+)'?:", ok)

    page.wait_for_timeout(500)

    # -----------------------------------------------------------
    # 2) Obtener la lista completa de localidades (una sola vez)
    # -----------------------------------------------------------
    dropdown_localidad = abrir_selector(page, SELECTOR_LOCALIDAD)
    localidades = listar_opciones(page, dropdown_localidad)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    print(f"\nTotal de localidades encontradas: {len(localidades)}\n")
    for i, nombre in enumerate(localidades):
        print(i, "->", nombre)

    # Quitar "Todas" (no es una localidad puntual)
    localidades = [
        loc for loc in localidades if loc.strip().lower() != "todas"
    ]

    # -----------------------------------------------------------
    # 3) Por cada localidad -> por cada barrio -> descargar CSV
    #    (sin límites: se procesan TODAS las localidades y barrios)
    # -----------------------------------------------------------
    resultados = {}

    for nombre_localidad in localidades:
        print(f"\n=== Localidad: {nombre_localidad} ===")

        dropdown_localidad = abrir_selector(page, SELECTOR_LOCALIDAD)
        ok = seleccionar_opcion(
            page, dropdown_localidad, nombre_localidad, exacto=True
        )
        if not ok:
            print(f"  No se pudo seleccionar la localidad '{nombre_localidad}', se omite.")
            continue

        page.wait_for_timeout(1200)  # tiempo para que Streamlit re-renderice

        dropdown_sector = abrir_selector(page, SELECTOR_SECTOR)
        barrios = listar_opciones(page, dropdown_sector, max_intentos=200)
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        print(f"  {len(barrios)} barrios encontrados")

        resultados[nombre_localidad] = {}

        for nombre_barrio in barrios:
            valor = None
            ultimo_error = None

            for intento in range(1, MAX_REINTENTOS_DESCARGA + 1):
                try:
                    dropdown_sector = abrir_selector(page, SELECTOR_SECTOR)
                    ok = seleccionar_opcion(
                        page, dropdown_sector, nombre_barrio, exacto=True
                    )
                    if not ok:
                        print(f"    [{nombre_barrio}] no se pudo seleccionar, se omite.")
                        break

                    # Espera creciente: si el intento anterior fue muy
                    # rápido para el grid, este le da más margen.
                    page.wait_for_timeout(ESPERA_BASE_MS * intento)

                    nombre_archivo = (
                        f"{sanitizar_nombre(nombre_localidad)}__"
                        f"{sanitizar_nombre(nombre_barrio)}.csv"
                    )
                    ruta_csv = descargar_csv(page, nombre_archivo)

                    if not csv_tiene_contenido(ruta_csv):
                        print(
                            f"    [{nombre_barrio}] intento {intento}/{MAX_REINTENTOS_DESCARGA}: "
                            f"CSV vacío (grid no había cargado), reintentando..."
                        )
                        continue

                    valor = extraer_valor_desde_csv(ruta_csv)
                    break

                except Exception as e:
                    ultimo_error = e
                    print(f"    [{nombre_barrio}] intento {intento} ERROR: {e}")
                    continue

            if valor is None:
                if ultimo_error is not None:
                    print(f"    [{nombre_barrio}] se omite tras agotar reintentos ({ultimo_error}).")
                else:
                    print(f"    [{nombre_barrio}] se omite: no se obtuvo un CSV con contenido tras {MAX_REINTENTOS_DESCARGA} intentos.")
                continue

            resultados[nombre_localidad][nombre_barrio] = valor
            print(f"    {nombre_barrio} -> {valor}")

        # Guardado incremental por si el script se cae a mitad de camino
        with open(ARCHIVO_SALIDA_JSON, "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)

        # También regeneramos la tabla consolidada en cada localidad,
        # así queda un CSV parcial actualizado si el script se detiene.
        tabla_parcial = construir_tabla_final(resultados)
        tabla_parcial.to_csv(ARCHIVO_SALIDA_CSV, index=False, encoding="utf-8-sig")

    print(f"\nResultado (detalle JSON) guardado en: {ARCHIVO_SALIDA_JSON}")

    # -----------------------------------------------------------
    # 4) Tabla final: localidad | barrio | total_personas_mayores
    # -----------------------------------------------------------
    tabla_final = construir_tabla_final(resultados)
    tabla_final.to_csv(ARCHIVO_SALIDA_CSV, index=False, encoding="utf-8-sig")

    print(f"Tabla final consolidada guardada en: {ARCHIVO_SALIDA_CSV}")
    print("\nVista previa de la tabla final:")
    print(tabla_final.to_string(index=False))

    input("\nPresiona ENTER para cerrar...")
    browser.close()