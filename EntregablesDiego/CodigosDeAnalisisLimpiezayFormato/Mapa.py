"""
Mapa de calor interactivo por barrio - Bogota
==============================================

Permite elegir que mapa generar:

    1. Poblacion adulta
    2. Poblacion mayor

El programa busca automaticamente los CSV en:

    CSVUsados/
    +-- Generados/
        +-- PoblacionAdulta/
        +-- PoblacionMayor/

Y guarda todos los archivos relacionados con el mapa en:

    MapasUsados/
    +-- PoblacionAdulta/
    +-- PoblacionMayor/

No utiliza rutas absolutas, por lo que el proyecto puede ser
descargado y ejecutado desde cualquier computador.

Instalacion:

    pip install geopandas folium branca requests pandas shapely pyproj fiona

Ejecucion:

    python mapa_calor.py
"""

import os
import re
import zipfile
import difflib
import unicodedata
from pathlib import Path

import requests
import pandas as pd
import geopandas as gpd
import folium
import branca.colormap as cm


# =====================================================================
# 1. RUTAS DEL PROYECTO
# =====================================================================

# Este archivo esta dentro de:
#
# EntregablesDiego/
# +-- CodigosdeAnalisisLimpiezasyFormato/
#     +-- mapa_calor.py
#
# Por tanto:
#
# parent        -> CodigosdeAnalisisLimpiezasyFormato
# parent.parent -> EntregablesDiego

CARPETA_CODIGOS = Path(__file__).resolve().parent

CARPETA_PROYECTO = CARPETA_CODIGOS.parent

CARPETA_CSV = (
    CARPETA_PROYECTO
    / "CSVUsados"
    / "Generados"
)

CARPETA_MAPAS = (
    CARPETA_PROYECTO
    / "MapasUsados"
)


# =====================================================================
# 2. CONFIGURACION DE LOS TIPOS DE POBLACION
# =====================================================================

CONFIGURACIONES = {

    "1": {
        "nombre": "Poblacion adulta",

        "carpeta": "PoblacionAdulta",

        "archivo": "personas_Adultas_por_barrio_resumen.csv",

        "columna_valor": "total_personas_adultas",

        "columna_raw": "total_personas_adultas_raw",

        "nombre_mapa": "mapa_personas_adultas_bogota.html",

        "titulo": "Personas adultas por barrio",
    },

    "2": {
        "nombre": "Poblacion mayor",

        "carpeta": "PoblacionMayor",

        "archivo": "personas_Mayores_por_barrio_resumen.csv",

        "columna_valor": "total_personas_mayores",

        "columna_raw": "total_personas_mayores_raw",

        "nombre_mapa": "mapa_personas_mayores_bogota.html",

        "titulo": "Personas mayores por barrio",
    },
}


# =====================================================================
# 3. URL DE LOS LIMITES DE BARRIOS
# =====================================================================

URL_BARRIOS = (
    "https://datosabiertos.bogota.gov.co/dataset/6f5031cf-07d0-42c3-ba5c-"
    "4436eba0a2d9/resource/428a5f4e-b9d4-4d91-88a7-28fb404a08ab/download/"
    "sector.geojson.07.26.zip"
)


# =====================================================================
# 4. NORMALIZACION DE NOMBRES
# =====================================================================

def normalizar(texto):

    if pd.isna(texto):
        return ""

    texto = str(texto).strip().upper()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    ).encode(
        "ascii",
        "ignore"
    ).decode("utf-8")

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto


# =====================================================================
# 5. MENU
# =====================================================================

def seleccionar_poblacion():

    print()
    print("=" * 60)
    print("       GENERADOR DE MAPA DE CALOR - BOGOTA")
    print("=" * 60)
    print()
    print("Que mapa quieres generar?")
    print()
    print("1. Poblacion adulta")
    print("2. Poblacion mayor")
    print("3. Salir")
    print()

    while True:

        opcion = input(
            "Selecciona una opcion [1-3]: "
        ).strip()

        if opcion in CONFIGURACIONES:

            return CONFIGURACIONES[opcion]

        if opcion == "3":

            print()
            print("Programa terminado.")
            return None

        print()
        print("[ERROR] Opcion no valida.")
        print("Selecciona 1, 2 o 3.")
        print()


# =====================================================================
# 6. DESCARGAR LIMITES DE BARRIOS
# =====================================================================

def descargar_barrios(carpeta_mapa):

    dest_zip = (
        carpeta_mapa
        / "sector_catastral.zip"
    )

    dest_dir = (
        carpeta_mapa
        / "sector_catastral"
    )


    # ---------------------------------------------------------------
    # Si ya existe, no volver a descargar
    # ---------------------------------------------------------------

    if dest_dir.exists():

        print()
        print("[OK] Los limites de barrios ya estan descargados.")

    else:

        print()
        print("Descargando limites oficiales de barrios de Bogota...")
        print("Esta operacion puede tardar un poco.")

        r = requests.get(
            URL_BARRIOS,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=180
        )

        r.raise_for_status()

        with open(
            dest_zip,
            "wb"
        ) as f:

            f.write(r.content)

        print("[OK] Descarga terminada.")


        # -----------------------------------------------------------
        # Extraer ZIP
        # -----------------------------------------------------------

        print("Extrayendo archivos...")

        with zipfile.ZipFile(
            dest_zip
        ) as z:

            z.extractall(
                dest_dir
            )

        print("[OK] Extraccion terminada.")


    # ---------------------------------------------------------------
    # Buscar GeoJSON
    # ---------------------------------------------------------------

    geojson_path = None

    for root, _, files in os.walk(
        dest_dir
    ):

        for fn in files:

            if fn.lower().endswith(
                (".geojson", ".json")
            ):

                geojson_path = (
                    Path(root) / fn
                )

                break

        if geojson_path:
            break


    if geojson_path is None:

        raise FileNotFoundError(
            "No se encontro un archivo "
            ".geojson o .json dentro de "
            "'sector_catastral'."
        )


    print()
    print("Leyendo geometria:")
    print(geojson_path)


    gdf = gpd.read_file(
        geojson_path
    )


    if gdf.crs is None:

        gdf.set_crs(
            epsg=4686,
            inplace=True
        )


    gdf = gdf.to_crs(
        epsg=4326
    )


    return gdf


# =====================================================================
# 7. GENERAR MAPA
# =====================================================================

def generar_mapa(config):

    nombre_carpeta = config["carpeta"]


    # ---------------------------------------------------------------
    # Ubicacion del CSV
    # ---------------------------------------------------------------

    archivo_csv = (
        CARPETA_CSV
        / nombre_carpeta
        / config["archivo"]
    )


    # ---------------------------------------------------------------
    # Verificar CSV
    # ---------------------------------------------------------------

    if not archivo_csv.exists():

        print()
        print("=" * 60)
        print("[ERROR] NO SE ENCONTRO EL ARCHIVO")
        print("=" * 60)

        print()
        print(archivo_csv)

        print()
        print(
            "Verifica que el CSV haya sido generado previamente."
        )

        return


    # ---------------------------------------------------------------
    # Crear carpeta del mapa
    # ---------------------------------------------------------------

    carpeta_mapa = (
        CARPETA_MAPAS
        / nombre_carpeta
    )

    carpeta_mapa.mkdir(
        parents=True,
        exist_ok=True
    )


    print()
    print("=" * 60)
    print(
        "GENERANDO MAPA: "
        + config["nombre"]
    )
    print("=" * 60)


    print()
    print("CSV utilizado:")
    print(archivo_csv)

    print()
    print("Archivos del mapa:")
    print(carpeta_mapa)


    # =================================================================
    # LEER CSV
    # =================================================================

    print()
    print("Leyendo CSV...")

    df = pd.read_csv(
        archivo_csv
    )


    columna_valor = (
        config["columna_valor"]
    )

    columna_raw = (
        config["columna_raw"]
    )


    # ---------------------------------------------------------------
    # Verificar columnas
    # ---------------------------------------------------------------

    columnas_necesarias = [
        "localidad",
        "barrio",
        columna_valor,
        columna_raw
    ]


    faltantes = [
        c
        for c in columnas_necesarias
        if c not in df.columns
    ]


    if faltantes:

        raise ValueError(
            "Faltan las siguientes columnas en el CSV:\n"
            + "\n".join(
                "- " + x
                for x in faltantes
            )
        )


    # =================================================================
    # LIMPIEZA
    # =================================================================

    df_barrios = df[
        df["barrio"]
        .astype(str)
        .str.strip()
        .str.lower()
        != "todos"
    ].copy()


    df_barrios[
        columna_valor
    ] = pd.to_numeric(
        df_barrios[
            columna_valor
        ],
        errors="coerce"
    )


    df_barrios = df_barrios.dropna(
        subset=[
            columna_valor
        ]
    )


    df_barrios[
        "barrio_norm"
    ] = df_barrios[
        "barrio"
    ].apply(
        normalizar
    )


    # =================================================================
    # DUPLICADOS
    # =================================================================

    if df_barrios[
        "barrio_norm"
    ].duplicated().any():

        dup = df_barrios[
            df_barrios[
                "barrio_norm"
            ].duplicated(
                keep=False
            )
        ]


        print()
        print(
            "[AVISO] Hay nombres de barrio repetidos "
            "en distintas localidades:"
        )


        print(
            dup[
                ["localidad", "barrio"]
            ].to_string(
                index=False
            )
        )


        df_barrios = (
            df_barrios
            .drop_duplicates(
                subset="barrio_norm",
                keep="first"
            )
        )


    # =================================================================
    # GEOMETRIA
    # =================================================================

    barrios_gdf = descargar_barrios(
        carpeta_mapa
    )


    barrios_gdf[
        "barrio_norm"
    ] = barrios_gdf[
        "SCANOMBRE"
    ].apply(
        normalizar
    )


    barrios_dis = (
        barrios_gdf
        .dissolve(
            by="barrio_norm",
            as_index=False
        )
    )


    # =================================================================
    # CRUCE
    # =================================================================

    print()
    print("Cruzando datos con la geometria de barrios...")

    merged = barrios_dis.merge(
        df_barrios[
            [
                "localidad",
                "barrio",
                "barrio_norm",
                columna_valor,
                columna_raw
            ]
        ],
        on="barrio_norm",
        how="right"
    )


    # =================================================================
    # MATCH DIFUSO
    # =================================================================

    sin_match = merged[
        merged.geometry.isna()
    ]


    if len(sin_match):

        print()
        print(
            "[AVISO] "
            + str(len(sin_match))
            + " barrios sin coincidencia geografica exacta."
        )

        print(
            "Intentando emparejamiento aproximado..."
        )


        catalogo = (
            barrios_dis[
                "barrio_norm"
            ]
            .tolist()
        )


        for idx, row in (
            sin_match.iterrows()
        ):

            candidatos = (
                difflib.get_close_matches(
                    row["barrio_norm"],
                    catalogo,
                    n=1,
                    cutoff=0.82
                )
            )


            if candidatos:

                geom = barrios_dis.loc[
                    barrios_dis[
                        "barrio_norm"
                    ] == candidatos[0],
                    "geometry"
                ].values[0]


                merged.loc[
                    idx,
                    "geometry"
                ] = geom


                print(
                    "  [OK] "
                    + "'"
                    + str(row["barrio"])
                    + "' -> '"
                    + str(candidatos[0])
                    + "'"
                )


            else:

                print(
                    "  [SIN MATCH] "
                    + "'"
                    + str(row["barrio"])
                    + "' sin coincidencia."
                )


    # =================================================================
    # GEODATAFRAME
    # =================================================================

    merged = gpd.GeoDataFrame(
        merged,
        geometry="geometry",
        crs="EPSG:4326"
    )


    antes = len(
        merged
    )


    merged = merged.dropna(
        subset=["geometry"]
    )


    print()
    print(
        "Barrios graficados: "
        + str(len(merged))
        + " de "
        + str(antes)
    )


    # =================================================================
    # MAPA
    # =================================================================

    print()
    print("Generando mapa...")


    m = folium.Map(
        location=[
            4.65,
            -74.1
        ],
        zoom_start=11,
        tiles="cartodbpositron"
    )


    minimo = merged[
        columna_valor
    ].min()


    maximo = merged[
        columna_valor
    ].max()


    colormap = (
        cm.linear.YlOrRd_09
        .scale(
            minimo,
            maximo
        )
    )


    colormap.caption = (
        config["titulo"]
    )


    colormap.add_to(
        m
    )


    # =================================================================
    # ESTILO
    # =================================================================

    def estilo(feature):

        valor = feature[
            "properties"
        ].get(
            columna_valor
        )


        return {

            "fillColor":
                colormap(valor)
                if valor is not None
                else "#cccccc",

            "color":
                "black",

            "weight":
                0.4,

            "fillOpacity":
                0.75,
        }


    # =================================================================
    # GEOJSON
    # =================================================================

    folium.GeoJson(

        merged,

        style_function=estilo,

        highlight_function=lambda f: {
            "weight": 2,
            "color": "#2222ff"
        },

        tooltip=folium.GeoJsonTooltip(

            fields=[
                "barrio",
                "localidad"
            ],

            aliases=[
                "Barrio:",
                "Localidad:"
            ],

        ),

        popup=folium.GeoJsonPopup(

            fields=[
                "localidad",
                "barrio",
                columna_raw
            ],

            aliases=[
                "Localidad:",
                "Barrio:",
                config["titulo"] + ":"
            ],

        ),

    ).add_to(
        m
    )


    # =================================================================
    # GUARDAR MAPA
    # =================================================================

    salida = (
        carpeta_mapa
        / config["nombre_mapa"]
    )


    m.save(
        salida
    )


    # =================================================================
    # FINAL
    # =================================================================

    print()
    print("=" * 60)
    print("[OK] MAPA GENERADO CORRECTAMENTE")
    print("=" * 60)

    print()
    print("Archivo:")
    print(salida)

    print()


# =====================================================================
# 8. PROGRAMA PRINCIPAL
# =====================================================================

def main():

    config = seleccionar_poblacion()

    if config is None:
        return


    try:

        generar_mapa(
            config
        )

    except Exception as e:

        print()
        print("=" * 60)
        print("[ERROR] OCURRIO UN ERROR")
        print("=" * 60)

        print()
        print(str(e))

        raise


# =====================================================================
# EJECUTAR
# =====================================================================

if __name__ == "__main__":

    main()