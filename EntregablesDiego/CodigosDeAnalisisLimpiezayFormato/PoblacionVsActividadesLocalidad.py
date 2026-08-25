"""
Analisis: relacion entre clases por semana (IDRD, hoja 4)
y poblacion por localidad (Bogota)

Permite analizar:

1. Poblacion adulta
2. Poblacion mayor
3. Ambas

Las clases se toman de la hoja 4 del archivo:

CSVUsados/Descargados/datos_por_localidad.xlsx

Los CSV de poblacion se toman de:

CSVUsados/Generados/PoblacionAdulta/PoblacionAdultaBarrio.csv
CSVUsados/Generados/PoblacionMayor/personas_Mayores_por_barrio_resumen.csv

Los resultados se guardan en sus respectivas carpetas.

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
# EntregablesDiego/
# +-- CodigosdeAnalisisLimpiezasyFormato/
#     +-- este_script.py
#
# Por tanto, el proyecto es la carpeta padre.

CARPETA_CODIGOS = Path(__file__).resolve().parent

CARPETA_PROYECTO = CARPETA_CODIGOS.parent


# =====================================================================
# 2. ARCHIVO DE CLASES
# =====================================================================

XLSX_PATH = (
    CARPETA_PROYECTO
    / "CSVUsados"
    / "Descargados"
    / "datos_por_localidad.xlsx"
)


# Hoja 4 del Excel.
# Pandas cuenta desde 0:
# hoja 1 -> 0
# hoja 2 -> 1
# hoja 3 -> 2
# hoja 4 -> 3

HOJA_CLASES = 3


# =====================================================================
# 3. CONFIGURACION DE POBLACIONES
# =====================================================================

CONFIGURACIONES = {

    "1": {
        "nombre": "Poblacion adulta",

        "carpeta": "PoblacionAdulta",

        "archivo": "personas_Adultas_por_barrio_resumen.csv",

        "columna": "total_personas_adultas",

        "salida_csv": "clases_vs_poblacion_adulta.csv",

        "salida_png": "clases_vs_poblacion_adulta.png",

        "titulo": (
            "Clases por semana (IDRD) vs. "
            "poblacion adulta por localidad"
        ),

        "nombre_eje_x": "Personas adultas (localidad)",

        "nombre_poblacion": "Personas adultas",
    },


    "2": {
        "nombre": "Poblacion mayor",

        "carpeta": "PoblacionMayor",

        "archivo": "personas_Mayores_por_barrio_resumen.csv",

        "columna": "total_personas_mayores",

        "salida_csv": "clases_vs_poblacion_mayor.csv",

        "salida_png": "clases_vs_poblacion_mayor.png",

        "titulo": (
            "Clases por semana (IDRD) vs. "
            "poblacion mayor por localidad"
        ),

        "nombre_eje_x": "Personas mayores (localidad)",

        "nombre_poblacion": "Personas mayores",
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
            "nan": "0",
            "None": "0"
        })
        .astype(float)
    )


# =====================================================================
# 6. SELECCIONAR ANALISIS
# =====================================================================

def seleccionar_analisis():

    print()
    print("=" * 60)
    print(" ANALISIS CLASES IDRD VS POBLACION")
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
# 7. VERIFICAR ARCHIVO DE CLASES
# =====================================================================

def verificar_archivo_clases():

    print()
    print("Archivo de clases:")

    print(XLSX_PATH)

    if not XLSX_PATH.exists():

        raise FileNotFoundError(
            "No se encontro el archivo de clases:\n"
            + str(XLSX_PATH)
        )

    print("[OK] Archivo de clases encontrado.")


# =====================================================================
# 8. CARGAR CLASES POR SEMANA
# =====================================================================

def cargar_clases():

    print()
    print("Cargando clases IDRD...")

    print(
        "Hoja:",
        HOJA_CLASES + 1
    )

    df_clases = pd.read_excel(
        XLSX_PATH,
        sheet_name=HOJA_CLASES
    )


    # ---------------------------------------------------------------
    # Limpiar nombres de columnas
    # ---------------------------------------------------------------

    df_clases.columns = [

        str(c).strip()

        for c in df_clases.columns
    ]


    # ---------------------------------------------------------------
    # Columnas numericas
    # ---------------------------------------------------------------

    cols_num = [

        "Clases por semana",

        "Escenarios con clases",

        "Disciplinas distintas",
    ]


    for col in cols_num:

        if col in df_clases.columns:

            df_clases[col] = a_numero(
                df_clases[col]
            )


    # ---------------------------------------------------------------
    # Verificar columnas
    # ---------------------------------------------------------------

    columnas_necesarias = [

        "Localidad",

        "Clases por semana",

        "Escenarios con clases",

        "Disciplinas distintas",
    ]


    faltantes = [

        col

        for col in columnas_necesarias

        if col not in df_clases.columns
    ]


    if faltantes:

        raise ValueError(
            "Faltan columnas en la hoja de clases:\n"
            + "\n".join(
                "- " + c
                for c in faltantes
            )
        )


    # ---------------------------------------------------------------
    # Normalizar localidad
    # ---------------------------------------------------------------

    df_clases["localidad_norm"] = (

        df_clases["Localidad"]

        .apply(normaliza)
    )


    print(
        "[OK] Clases cargadas."
    )

    print(
        "Localidades:",
        len(df_clases)
    )


    return df_clases


# =====================================================================
# 9. CARGAR POBLACION
# =====================================================================

def cargar_poblacion(config):

    carpeta = (

        CARPETA_PROYECTO

        / "CSVUsados"

        / "Generados"

        / config["carpeta"]
    )


    csv_path = (

        carpeta

        / config["archivo"]
    )


    print()
    print(
        "Cargando:",
        config["nombre"]
    )

    print("Archivo:")

    print(csv_path)


    if not csv_path.exists():

        raise FileNotFoundError(
            "No se encontro el CSV:\n"
            + str(csv_path)
        )


    # ---------------------------------------------------------------
    # Leer CSV
    # ---------------------------------------------------------------

    df_personas = pd.read_csv(
        csv_path
    )


    # ---------------------------------------------------------------
    # Limpiar nombres de columnas
    # ---------------------------------------------------------------

    df_personas.columns = [

        str(c).strip().lower()

        for c in df_personas.columns
    ]


    # ---------------------------------------------------------------
    # Verificar columnas
    # ---------------------------------------------------------------

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

    df_localidad["localidad_norm"] = (

        df_localidad["localidad"]

        .apply(normaliza)
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


    # ---------------------------------------------------------------
    # Cambiar nombre de localidad del CSV
    # ---------------------------------------------------------------

    df_localidad = (

        df_localidad.rename(

            columns={
                "localidad": "Localidad_csv"
            }
        )
    )


    # ---------------------------------------------------------------
    # Convertir poblacion a numero
    # ---------------------------------------------------------------

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
    df_clases,
    df_personas,
    config
):

    columna = config["columna"]


    print()
    print(
        "Cruzando clases con",
        config["nombre"].lower() + "..."
    )


    df = df_clases.merge(

        df_personas,

        on="localidad_norm",

        how="left"
    )


    # ---------------------------------------------------------------
    # Revisar localidades sin coincidencia
    # ---------------------------------------------------------------

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


    # ---------------------------------------------------------------
    # Eliminar localidades sin poblacion
    # ---------------------------------------------------------------

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


    # ---------------------------------------------------------------
    # Clases por cada 1000 personas
    # ---------------------------------------------------------------

    df[
        "clases_por_1000_personas"
    ] = (

        df[
            "Clases por semana"
        ]

        * 1000

        /

        df[
            columna
        ]
    )


    # ---------------------------------------------------------------
    # Escenarios por cada 1000 personas
    # ---------------------------------------------------------------

    df[
        "escenarios_por_1000_personas"
    ] = (

        df[
            "Escenarios con clases"
        ]

        * 1000

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

    # Eliminar valores no numericos
    datos = pd.concat(
        [
            pd.to_numeric(
                x,
                errors="coerce"
            ),

            pd.to_numeric(
                y,
                errors="coerce"
            )
        ],
        axis=1
    ).dropna()


    if len(datos) < 2:

        print(
            nombre_x
            + " vs "
            + nombre_y
            + ": no hay suficientes datos."
        )

        return np.nan, np.nan


    r, p = pearsonr(

        datos.iloc[:, 0],

        datos.iloc[:, 1]
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


# =====================================================================
# 13. CALCULAR CORRELACIONES
# =====================================================================

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


    # ---------------------------------------------------------------
    # Poblacion vs clases
    # ---------------------------------------------------------------

    reporta_correlacion(

        df[columna],

        df[
            "Clases por semana"
        ],

        config["nombre"],

        "Clases por semana"
    )


    # ---------------------------------------------------------------
    # Poblacion vs escenarios
    # ---------------------------------------------------------------

    reporta_correlacion(

        df[columna],

        df[
            "Escenarios con clases"
        ],

        config["nombre"],

        "Escenarios con clases"
    )


    # ---------------------------------------------------------------
    # Poblacion vs disciplinas
    # ---------------------------------------------------------------

    reporta_correlacion(

        df[columna],

        df[
            "Disciplinas distintas"
        ],

        config["nombre"],

        "Disciplinas distintas"
    )


# =====================================================================
# 14. TABLA
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

            "Clases por semana",

            "Escenarios con clases",

            "Disciplinas distintas",

            "clases_por_1000_personas",

            "escenarios_por_1000_personas",
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


    # ---------------------------------------------------------------
    # Carpeta de salida
    # ---------------------------------------------------------------

    carpeta_salida = (

        CARPETA_PROYECTO

        / "CSVUsados"

        / "Generados"

        / config["carpeta"]
    )


    carpeta_salida.mkdir(

        parents=True,

        exist_ok=True
    )


    # ---------------------------------------------------------------
    # Guardar CSV
    # ---------------------------------------------------------------

    archivo_salida = (

        carpeta_salida

        / config["salida_csv"]
    )


    tabla.to_csv(

        archivo_salida,

        index=False,

        encoding="utf-8-sig"
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
# 15. GRAFICO
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


    # ---------------------------------------------------------------
    # Datos
    # ---------------------------------------------------------------

    x = df[
        columna
    ].values


    y = df[
        "Clases por semana"
    ].values


    # ---------------------------------------------------------------
    # Puntos
    # ---------------------------------------------------------------

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
                    "Clases por semana"
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

    if len(x) >= 2 and np.ptp(x) > 0:

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

        "Clases por semana"
    )


    ax.set_title(

        config["titulo"]
    )


    ax.legend()


    plt.tight_layout()


    # ---------------------------------------------------------------
    # Carpeta de salida
    # ---------------------------------------------------------------

    carpeta_salida = (

        CARPETA_PROYECTO

        / "CSVUsados"

        / "Generados"

        / config["carpeta"]
    )


    carpeta_salida.mkdir(

        parents=True,

        exist_ok=True
    )


    # ---------------------------------------------------------------
    # Guardar PNG
    # ---------------------------------------------------------------

    archivo_salida = (

        carpeta_salida

        / config["salida_png"]
    )


    plt.savefig(

        archivo_salida,

        dpi=150,

        bbox_inches="tight"
    )


    print()

    print(
        "[OK] Grafico guardado:"
    )

    print(
        archivo_salida
    )


    plt.show()

    plt.close()


# =====================================================================
# 16. EJECUTAR UN ANALISIS
# =====================================================================

def ejecutar_analisis(
    df_clases,
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

        df_clases,

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
# 17. MAIN
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
        # Verificar archivo
        # -----------------------------------------------------------

        verificar_archivo_clases()


        # -----------------------------------------------------------
        # Cargar clases una sola vez
        # -----------------------------------------------------------

        df_clases = cargar_clases()


        # -----------------------------------------------------------
        # Ejecutar analisis seleccionados
        # -----------------------------------------------------------

        for config in configuraciones:

            ejecutar_analisis(

                df_clases,

                config
            )


        # -----------------------------------------------------------
        # Final
        # -----------------------------------------------------------

        print()
        print("=" * 60)

        print(
            "[OK] TODOS LOS ANALISIS TERMINARON"
        )

        print("=" * 60)

        print()


    except Exception as e:

        print()
        print("=" * 60)

        print(
            "[ERROR] OCURRIO UN ERROR"
        )

        print("=" * 60)

        print()

        print(
            str(e)
        )

        raise


# =====================================================================
# EJECUCION
# =====================================================================

if __name__ == "__main__":

    main()