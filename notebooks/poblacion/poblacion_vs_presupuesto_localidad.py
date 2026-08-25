"""
Analisis: relacion entre presupuesto IDRD y poblacion por localidad
(Bogota)

Permite analizar:

1. Poblacion adulta
2. Poblacion mayor
3. Ambas

El presupuesto se toma del archivo:

data/raw/datos_por_localidad.xlsx

Los CSV de poblacion se toman de:

data/processed/poblacion_adulta/personas_Adultas_por_barrio_resumen.csv
data/processed/poblacion_mayor/personas_Mayores_por_barrio_resumen.csv

Los CSV de resultado se guardan junto a la poblacion usada y los
graficos en outputs/figuras/.

No se utilizan rutas absolutas, por lo que el proyecto puede
ser descargado y ejecutado desde cualquier computador.
"""

import unicodedata
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from scipy.stats import pearsonr


# =====================================================================
# 1. RUTAS DEL PROYECTO
# =====================================================================

# Este script esta dentro de:
#
# notebooks/
# +-- poblacion/
#     +-- este_script.py
#
# Por tanto, la raiz del repositorio esta dos niveles arriba.

CARPETA_CODIGOS = Path(__file__).resolve().parent

RAIZ = CARPETA_CODIGOS.parents[1]

# Los datos generados van a data/processed/;
# las figuras a outputs/figuras/.
CARPETA_GENERADOS = RAIZ / "data" / "processed"

CARPETA_FIGURAS = RAIZ / "outputs" / "figuras"


# =====================================================================
# 2. ARCHIVO DE PRESUPUESTO
# =====================================================================

XLSX_PATH = RAIZ / "data" / "raw" / "datos_por_localidad.xlsx"


# =====================================================================
# 3. CONFIGURACION DE POBLACIONES
# =====================================================================

CONFIGURACIONES = {

    "1": {
        "nombre": "Poblacion adulta",

        "carpeta": "poblacion_adulta",

        "archivo": "personas_Adultas_por_barrio_resumen.csv",

        "columna": "total_personas_adultas",

        "salida_csv": "presupuesto_vs_poblacion_adulta.csv",

        "salida_png": "presupuesto_vs_poblacion_adulta.png",

        "titulo": (
            "Presupuesto IDRD programado vs. "
            "poblacion adulta por localidad"
        ),

        "nombre_eje_x": "Personas adultas (localidad)",
    },


    "2": {
        "nombre": "Poblacion mayor",

        "carpeta": "poblacion_mayor",

        "archivo": "personas_Mayores_por_barrio_resumen.csv",

        "columna": "total_personas_mayores",

        "salida_csv": "presupuesto_vs_poblacion_mayor.csv",

        "salida_png": "presupuesto_vs_poblacion_mayor.png",

        "titulo": (
            "Presupuesto IDRD programado vs. "
            "poblacion mayor por localidad"
        ),

        "nombre_eje_x": "Personas mayores (localidad)",
    },
}


# =====================================================================
# 4. NORMALIZAR NOMBRES
# =====================================================================

def normaliza(texto: str) -> str:

    texto = str(texto).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        c
        for c in texto
        if not unicodedata.combining(c)
    )

    return texto


# =====================================================================
# 5. CONVERTIR A NUMERO
# =====================================================================

def a_numero(serie: pd.Series) -> pd.Series:

    if pd.api.types.is_numeric_dtype(serie):
        return serie

    return (
        serie.astype(str)
        .str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .replace({
            "": "0",
            "nan": "0"
        })
        .astype(float)
    )


# =====================================================================
# 6. SELECCIONAR ANALISIS
# =====================================================================

def seleccionar_analisis():

    print()
    print("=" * 60)
    print(" ANALISIS PRESUPUESTO IDRD VS POBLACION")
    print("=" * 60)
    print()

    print("Que analisis quieres realizar?")
    print()

    print("1. Poblacion adulta")
    print("2. Poblacion mayor")
    print("3. Ambas")
    print("4. Salir")

    print()

    while True:

        opcion = input(
            "Selecciona una opcion [1-4]: "
        ).strip()

        if opcion in CONFIGURACIONES:

            return [
                CONFIGURACIONES[opcion]
            ]

        if opcion == "3":

            return list(
                CONFIGURACIONES.values()
            )

        if opcion == "4":

            print()
            print("Programa terminado.")

            return []

        print()
        print("[ERROR] Opcion no valida.")
        print("Selecciona 1, 2, 3 o 4.")
        print()


# =====================================================================
# 7. VERIFICAR ARCHIVO DE PRESUPUESTO
# =====================================================================

def verificar_presupuesto():

    print()
    print("Archivo de presupuesto:")
    print(XLSX_PATH)

    if not XLSX_PATH.exists():

        raise FileNotFoundError(
            "No se encontro el archivo de presupuesto:\n"
            + str(XLSX_PATH)
        )

    print("[OK] Archivo de presupuesto encontrado.")


# =====================================================================
# 8. CARGAR PRESUPUESTO
# =====================================================================

def cargar_presupuesto():

    print()
    print("Cargando presupuesto...")

    df_presupuesto = pd.read_excel(
        XLSX_PATH,
        sheet_name=0
    )

    df_presupuesto.columns = [
        str(c).strip()
        for c in df_presupuesto.columns
    ]


    cols_num = [

        "Actividad física directa (millones)",

        "Parques de proximidad (millones)",

        "Total programado (millones)",

        "Total girado (millones)",

        "% girado",
    ]


    for col in cols_num:

        if col in df_presupuesto.columns:

            df_presupuesto[col] = a_numero(
                df_presupuesto[col]
            )


    if "Localidad" not in df_presupuesto.columns:

        raise ValueError(
            "El archivo de presupuesto no contiene "
            "la columna 'Localidad'."
        )


    df_presupuesto["localidad_norm"] = (
        df_presupuesto["Localidad"]
        .apply(normaliza)
    )


    print("[OK] Presupuesto cargado.")

    return df_presupuesto


# =====================================================================
# 9. CARGAR POBLACION
# =====================================================================

def cargar_poblacion(config):

    carpeta = (
        CARPETA_GENERADOS
        / config["carpeta"]
    )


    csv_path = (
        carpeta
        / config["archivo"]
    )


    print()
    print("Cargando:", config["nombre"])

    print("Archivo:")
    print(csv_path)


    if not csv_path.exists():

        raise FileNotFoundError(
            "No se encontro el CSV:\n"
            + str(csv_path)
        )


    df_personas = pd.read_csv(
        csv_path
    )


    df_personas.columns = [
        str(c).strip().lower()
        for c in df_personas.columns
    ]


    columnas_necesarias = [

        "localidad",

        "barrio",

        config["columna"]
    ]


    faltantes = [

        c
        for c in columnas_necesarias

        if c not in df_personas.columns
    ]


    if faltantes:

        raise ValueError(
            "Faltan columnas en el CSV:\n"
            + "\n".join(
                "- " + c
                for c in faltantes
            )
        )


    # ---------------------------------------------------------------
    # Tomar solamente las filas "Todos"
    # ---------------------------------------------------------------

    df_localidad = (

        df_personas[
            df_personas["barrio"]
            .astype(str)
            .str.strip()
            .str.lower()
            == "todos"
        ]

        .copy()
    )


    # ---------------------------------------------------------------
    # Normalizar localidad
    # ---------------------------------------------------------------

    df_localidad[
        "localidad_norm"
    ] = (

        df_localidad["localidad"]

        .apply(
            normaliza
        )
    )


    # ---------------------------------------------------------------
    # Seleccionar columnas
    # ---------------------------------------------------------------

    df_localidad = (

        df_localidad[
            [
                "localidad_norm",

                "localidad",

                config["columna"]
            ]
        ]

        .copy()
    )


    df_localidad = (

        df_localidad.rename(
            columns={
                "localidad": "Localidad_csv"
            }
        )
    )


    df_localidad[
        config["columna"]
    ] = pd.to_numeric(

        df_localidad[
            config["columna"]
        ],

        errors="coerce"
    )


    print(
        "[OK] Poblacion cargada."
    )

    print(
        "Localidades:",
        len(df_localidad)
    )


    return df_localidad


# =====================================================================
# 10. CRUZAR DATOS
# =====================================================================

def cruzar_datos(
    df_presupuesto,
    df_personas,
    config
):

    columna = config["columna"]


    print()
    print(
        "Cruzando presupuesto con",
        config["nombre"].lower() + "..."
    )


    df = df_presupuesto.merge(

        df_personas,

        on="localidad_norm",

        how="left"
    )


    faltantes = (

        df[
            df[columna].isna()
        ]["Localidad"]

        .tolist()
    )


    if faltantes:

        print()

        print(
            "[AVISO] Localidades sin coincidencia:"
        )


        for localidad in faltantes:

            print(
                "  -",
                localidad
            )


    df = df.dropna(
        subset=[
            columna
        ]
    )


    print()

    print(
        "[OK] Cruce terminado."
    )

    print(
        "Localidades con informacion:",
        len(df)
    )


    return df


# =====================================================================
# 11. INDICADORES
# =====================================================================

def calcular_indicadores(
    df,
    config
):

    columna = config["columna"]


    df[
        "presupuesto_programado_por_persona"
    ] = (

        df[
            "Total programado (millones)"
        ]

        * 1_000_000

        /

        df[
            columna
        ]
    )


    df[
        "presupuesto_girado_por_persona"
    ] = (

        df[
            "Total girado (millones)"
        ]

        * 1_000_000

        /

        df[
            columna
        ]
    )


    return df


# =====================================================================
# 12. CORRELACION
# =====================================================================

def reporta_correlacion(
    x,
    y,
    nombre_x,
    nombre_y
):

    r, p = pearsonr(
        x,
        y
    )


    print(
        nombre_x
        + " vs "
        + nombre_y
        + ": r = "
        + f"{r:.3f}"
        + " (p-valor = "
        + f"{p:.4f}"
        + ")"
    )


    return r, p


def calcular_correlaciones(
    df,
    config
):

    columna = config["columna"]


    print()
    print("=" * 60)

    print(
        "CORRELACIONES - "
        + config["nombre"].upper()
    )

    print("=" * 60)


    reporta_correlacion(

        df[columna],

        df[
            "Total programado (millones)"
        ],

        config["nombre"],

        "Presupuesto programado"
    )


    reporta_correlacion(

        df[columna],

        df[
            "Total girado (millones)"
        ],

        config["nombre"],

        "Presupuesto girado"
    )


# =====================================================================
# 13. TABLA
# =====================================================================

def generar_tabla(
    df,
    config
):

    columna = config["columna"]


    tabla = df[
        [
            "Localidad",

            columna,

            "Total programado (millones)",

            "Total girado (millones)",

            "% girado",

            "presupuesto_programado_por_persona"
        ]
    ].sort_values(

        columna,

        ascending=False
    )


    print()
    print("=" * 60)

    print(
        "TABLA - "
        + config["nombre"].upper()
    )

    print("=" * 60)

    print()


    print(
        tabla.to_string(
            index=False
        )
    )


    carpeta_salida = (

        CARPETA_GENERADOS

        / config["carpeta"]
    )


    carpeta_salida.mkdir(
        parents=True,
        exist_ok=True
    )


    archivo_salida = (

        carpeta_salida

        / config["salida_csv"]
    )


    tabla.to_csv(
        archivo_salida,
        index=False
    )


    print()

    print(
        "[OK] Tabla guardada:"
    )

    print(
        archivo_salida
    )


    return tabla


# =====================================================================
# 14. GRAFICO
# =====================================================================

def generar_grafico(
    df,
    config
):

    columna = config["columna"]


    print()
    print(
        "Generando grafico de",
        config["nombre"].lower() + "..."
    )


    fig, ax = plt.subplots(
        figsize=(9, 6)
    )


    x = df[
        columna
    ].values


    y = df[
        "Total programado (millones)"
    ].values


    ax.scatter(
        x,
        y,
        color="#2563eb"
    )


    # ---------------------------------------------------------------
    # Nombres de localidades
    # ---------------------------------------------------------------

    for _, row in df.iterrows():

        ax.annotate(

            row["Localidad"],

            (
                row[columna],

                row[
                    "Total programado (millones)"
                ]
            ),

            fontsize=8,

            xytext=(
                4,
                4
            ),

            textcoords="offset points"
        )


    # ---------------------------------------------------------------
    # Linea de tendencia
    # ---------------------------------------------------------------

    m, b = np.polyfit(
        x,
        y,
        1
    )


    xs = np.linspace(
        x.min(),
        x.max(),
        100
    )


    ax.plot(

        xs,

        m * xs + b,

        color="#dc2626",

        linestyle="--",

        label="Tendencia"
    )


    # ---------------------------------------------------------------
    # Etiquetas
    # ---------------------------------------------------------------

    ax.set_xlabel(
        config["nombre_eje_x"]
    )


    ax.set_ylabel(
        "Presupuesto programado (millones COP)"
    )


    ax.set_title(
        config["titulo"]
    )


    ax.legend()


    plt.tight_layout()


    carpeta_salida = CARPETA_FIGURAS


    carpeta_salida.mkdir(
        parents=True,
        exist_ok=True
    )


    archivo_salida = (

        carpeta_salida

        / config["salida_png"]
    )


    plt.savefig(
        archivo_salida,
        dpi=150
    )


    print()

    print(
        "[OK] Grafico guardado:"
    )

    print(
        archivo_salida
    )


    plt.show()


# =====================================================================
# 15. EJECUTAR UN ANALISIS
# =====================================================================

def ejecutar_analisis(
    df_presupuesto,
    config
):

    print()
    print()
    print("#" * 60)

    print(
        "ANALISIS:",
        config["nombre"].upper()
    )

    print("#" * 60)


    # ---------------------------------------------------------------
    # Cargar poblacion
    # ---------------------------------------------------------------

    df_personas = cargar_poblacion(
        config
    )


    # ---------------------------------------------------------------
    # Cruzar
    # ---------------------------------------------------------------

    df = cruzar_datos(

        df_presupuesto,

        df_personas,

        config
    )


    # ---------------------------------------------------------------
    # Indicadores
    # ---------------------------------------------------------------

    df = calcular_indicadores(
        df,
        config
    )


    # ---------------------------------------------------------------
    # Correlaciones
    # ---------------------------------------------------------------

    calcular_correlaciones(
        df,
        config
    )


    # ---------------------------------------------------------------
    # Tabla
    # ---------------------------------------------------------------

    generar_tabla(
        df,
        config
    )


    # ---------------------------------------------------------------
    # Grafico
    # ---------------------------------------------------------------

    generar_grafico(
        df,
        config
    )


# =====================================================================
# 16. MAIN
# =====================================================================

def main():

    try:

        # -----------------------------------------------------------
        # Seleccionar analisis
        # -----------------------------------------------------------

        configuraciones = seleccionar_analisis()


        if not configuraciones:

            return


        # -----------------------------------------------------------
        # Verificar presupuesto
        # -----------------------------------------------------------

        verificar_presupuesto()


        # -----------------------------------------------------------
        # Cargar presupuesto una sola vez
        # -----------------------------------------------------------

        df_presupuesto = cargar_presupuesto()


        # -----------------------------------------------------------
        # Ejecutar analisis seleccionados
        # -----------------------------------------------------------

        for config in configuraciones:

            ejecutar_analisis(

                df_presupuesto,

                config
            )


        # -----------------------------------------------------------
        # Final
        # -----------------------------------------------------------

        print()
        print("=" * 60)
        print("[OK] TODOS LOS ANALISIS TERMINARON")
        print("=" * 60)
        print()


    except Exception as e:

        print()
        print("=" * 60)
        print("[ERROR] OCURRIO UN ERROR")
        print("=" * 60)

        print()
        print(str(e))

        raise


# =====================================================================
# EJECUCION
# =====================================================================

if __name__ == "__main__":

    main()