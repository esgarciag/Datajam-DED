"""
Priorizacion: indice de prioridad por barrio (Bogota)

Cruza tres fuentes para calcular, por barrio, un indice de prioridad de
inversion en actividad fisica:

1. Poblacion (adulta y/o mayor) por barrio, con su clave y localidad
   -> data/processed/poblacion_adulta/PoblacionAdultaBarrioNormalizado.csv
   -> data/processed/poblacion_mayor/personas_Mayores_por_barrio_resumen.csv

2. Porcentaje de sedentarismo por localidad (Encuesta Multiproposito 2021)
   -> data/raw/EncuestaMultiproposito2021ActividadFisica.csv

3. Oferta y ejecucion presupuestal por localidad (IDRD)
   -> data/raw/datos_por_localidad.xlsx
      hoja 1 (indice 0): Presupuesto por localidad
      hoja 4 (indice 3): Actividades por localidad

Permite calcular el indice para:

1. Poblacion adulta
2. Poblacion mayor
3. Ambas

El indice de prioridad combina (todo normalizado 0-1 por localidad o
por barrio, segun corresponda):

    (+) sedentarismo_norm        -> mas sedentarismo = mas prioridad
    (+) poblacion_norm           -> mas poblacion (del barrio) = mas prioridad
    (-) oferta_per_capita_norm   -> mas clases/escenarios por adulto = menos prioridad
    (-) ejecucion_per_capita_norm-> mas presupuesto girado por adulto = menos prioridad

En cada fila del resultado se preservan siempre "clave", "localidad" y
"barrio" del CSV de poblacion de origen.

Los CSV de resultado se guardan junto a la poblacion usada:

data/processed/poblacion_adulta/indice_prioridad_adulta.csv
data/processed/poblacion_mayor/indice_prioridad_mayor.csv

y los graficos en outputs/figuras/.

No se usan rutas absolutas: el proyecto puede descargarse y ejecutarse
desde cualquier computador.
"""

import unicodedata
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# =====================================================================
# 1. RUTAS DEL PROYECTO
# =====================================================================

# Este script esta dentro de:
#
# notebooks/
# +-- poblacion/
#     +-- priorizacion.py
#
# Por tanto, la raiz del repositorio esta dos niveles arriba.

CARPETA_CODIGOS = Path(__file__).resolve().parent

RAIZ = CARPETA_CODIGOS.parents[1]

CARPETA_DESCARGADOS = RAIZ / "data" / "raw"

CARPETA_GENERADOS = RAIZ / "data" / "processed"

CARPETA_FIGURAS = RAIZ / "outputs" / "figuras"


# =====================================================================
# 2. ARCHIVOS DE ENCUESTA Y DATOS POR LOCALIDAD (IDRD)
# =====================================================================

XLSX_PATH = CARPETA_DESCARGADOS / "datos_por_localidad.xlsx"

ENCUESTA_PATH = CARPETA_DESCARGADOS / "EncuestaMultiproposito2021ActividadFisica.csv"

# Hojas del Excel. Pandas cuenta desde 0:
# hoja 1 -> 0 (Presupuesto por localidad)
# hoja 4 -> 3 (Actividades por localidad)

HOJA_PRESUPUESTO = 0
HOJA_ACTIVIDADES = 3


# =====================================================================
# 3. CONFIGURACION DE POBLACIONES
# =====================================================================

CONFIGURACIONES = {

    "1": {
        "nombre": "Poblacion adulta",

        "carpeta": "poblacion_adulta",

        "archivo": "PoblacionAdultaBarrioNormalizado.csv",

        "separador": "\t",

        "columna_poblacion": "total_personas_adultas",

        "salida_csv": "indice_prioridad_adulta.csv",

        "salida_png": "indice_prioridad_adulta.png",

        "titulo": (
            "Indice de prioridad por barrio - "
            "poblacion adulta"
        ),

        "nombre_poblacion": "Personas adultas",
    },


    "2": {
        "nombre": "Poblacion mayor",

        "carpeta": "poblacion_mayor",

        "archivo": "personas_Mayores_por_barrio_resumen.csv",

        "separador": ",",

        "columna_poblacion": "total_personas_mayores",

        "salida_csv": "indice_prioridad_mayor.csv",

        "salida_png": "indice_prioridad_mayor.png",

        "titulo": (
            "Indice de prioridad por barrio - "
            "poblacion mayor"
        ),

        "nombre_poblacion": "Personas mayores",
    },
}


# Pesos del indice de prioridad. Deben sumar 1.

PESOS = {
    "sedentarismo": 0.35,
    "poblacion": 0.25,
    "oferta": 0.20,
    "ejecucion": 0.20,
}

assert abs(sum(PESOS.values()) - 1.0) < 1e-9, "Los pesos deben sumar 1"


# =====================================================================
# 4. FUNCIONES AUXILIARES
# =====================================================================

def normalizar_texto(serie: pd.Series) -> pd.Series:
    """
    Deja un texto en mayusculas, sin tildes y sin espacios de sobra,
    para poder cruzar localidades escritas de forma distinta en
    cada archivo.
    """
    return (
        serie.astype(str)
        .str.strip()
        .str.upper()
        .apply(lambda t: "".join(
            c for c in unicodedata.normalize("NFKD", t)
            if not unicodedata.combining(c)
        ))
    )


def minmax(serie: pd.Series) -> pd.Series:
    """Normaliza una serie numerica al rango 0-1."""
    rango = serie.max() - serie.min()
    if rango == 0:
        return serie * 0
    return (serie - serie.min()) / rango


def cargar_encuesta_sedentarismo() -> pd.DataFrame:
    """
    Carga el % de sedentarismo por localidad desde la Encuesta
    Multiproposito 2021.
    """
    encuesta = pd.read_csv(ENCUESTA_PATH)

    encuesta = encuesta[
        encuesta["Localidad"].str.upper() != "BOGOTÁ D.C."
    ].copy()

    encuesta["localidad_key"] = normalizar_texto(encuesta["Localidad"])

    encuesta = encuesta.rename(columns={
        "No practicó deporte ni tuvo actividad física en el mes":
            "pct_sedentarismo",
    })

    return encuesta[["localidad_key", "pct_sedentarismo"]]


def cargar_oferta_y_presupuesto() -> pd.DataFrame:
    """
    Carga, por localidad, el presupuesto girado y la oferta de clases
    del IDRD desde datos_por_localidad.xlsx.
    """
    xl = pd.ExcelFile(XLSX_PATH)

    presupuesto = xl.parse(xl.sheet_names[HOJA_PRESUPUESTO])
    presupuesto["localidad_key"] = normalizar_texto(presupuesto["Localidad"])
    presupuesto = presupuesto.rename(columns={
        "Total girado (millones)": "presupuesto_girado_millones",
        "% girado": "pct_girado",
    })
    presupuesto = presupuesto[[
        "localidad_key", "presupuesto_girado_millones", "pct_girado",
    ]]

    actividades = xl.parse(xl.sheet_names[HOJA_ACTIVIDADES])
    actividades["localidad_key"] = normalizar_texto(actividades["Localidad"])
    actividades = actividades.rename(columns={
        "Clases por semana": "clases_por_semana",
        "Escenarios con clases": "escenarios_con_clases",
    })
    actividades = actividades[[
        "localidad_key", "clases_por_semana", "escenarios_con_clases",
    ]]

    return presupuesto.merge(actividades, on="localidad_key", how="outer")


def cargar_poblacion(config: dict) -> pd.DataFrame:
    """
    Carga el CSV de poblacion por barrio indicado en la configuracion,
    y asegura que existan las columnas clave, localidad y barrio.
    """
    ruta = CARPETA_GENERADOS / config["carpeta"] / config["archivo"]

    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontro el archivo de poblacion:\n{ruta}\n"
            "Revisa que el archivo exista o ajusta CONFIGURACIONES."
        )

    pob = pd.read_csv(ruta, sep=config["separador"])

    # Quitar la fila resumen "Todos" por barrio, si existe
    # (es el total de la localidad, no un barrio real).
    if "barrio" in pob.columns:
        pob = pob[pob["barrio"].str.upper() != "TODOS"].copy()

    columnas_requeridas = {"localidad", "barrio", config["columna_poblacion"]}
    faltantes = columnas_requeridas - set(pob.columns)
    if faltantes:
        raise ValueError(
            f"Al archivo {ruta.name} le faltan las columnas: {faltantes}"
        )

    # Si no trae una columna "clave" ya construida, se genera aqui.
    if "clave" not in pob.columns:
        pob["clave"] = (
            normalizar_texto(pob["localidad"]) + "_" +
            normalizar_texto(pob["barrio"])
        )

    pob["localidad_key"] = normalizar_texto(pob["localidad"])

    return pob


# =====================================================================
# 5. CALCULO DEL INDICE DE PRIORIDAD
# =====================================================================

def calcular_indice_prioridad(config: dict) -> pd.DataFrame:
    """
    Calcula el indice de prioridad por barrio para la poblacion
    indicada en `config` (adulta o mayor).
    """
    columna_poblacion = config["columna_poblacion"]

    pob = cargar_poblacion(config)
    sedentarismo = cargar_encuesta_sedentarismo()
    oferta_presupuesto = cargar_oferta_y_presupuesto()

    # ---- agregados por localidad (para calcular indicadores per capita)
    pob_localidad = (
        pob.groupby("localidad_key", as_index=False)[columna_poblacion]
        .sum()
        .rename(columns={columna_poblacion: "poblacion_localidad"})
    )

    localidad = (
        pob_localidad
        .merge(sedentarismo, on="localidad_key", how="left")
        .merge(oferta_presupuesto, on="localidad_key", how="left")
    )

    localidad["clases_per_10k"] = (
        localidad["clases_por_semana"]
        / localidad["poblacion_localidad"] * 10_000
    )
    localidad["presupuesto_girado_per_10k"] = (
        localidad["presupuesto_girado_millones"]
        / localidad["poblacion_localidad"] * 10_000
    )

    localidad["sedentarismo_norm"] = minmax(localidad["pct_sedentarismo"])
    localidad["oferta_norm"] = minmax(localidad["clases_per_10k"])
    localidad["ejecucion_norm"] = minmax(localidad["presupuesto_girado_per_10k"])

    # ---- union a nivel barrio (se preservan clave, localidad, barrio)
    df = pob.merge(
        localidad[[
            "localidad_key", "pct_sedentarismo", "sedentarismo_norm",
            "clases_por_semana", "escenarios_con_clases", "oferta_norm",
            "presupuesto_girado_millones", "pct_girado", "ejecucion_norm",
        ]],
        on="localidad_key",
        how="left",
    )

    df["poblacion_norm"] = minmax(df[columna_poblacion])

    df["indice_prioridad"] = (
        PESOS["sedentarismo"] * df["sedentarismo_norm"]
        + PESOS["poblacion"] * df["poblacion_norm"]
        + PESOS["oferta"] * (1 - df["oferta_norm"])
        + PESOS["ejecucion"] * (1 - df["ejecucion_norm"])
    ) * 100

    df["indice_prioridad"] = df["indice_prioridad"].round(2)
    df["ranking_prioridad"] = (
        df["indice_prioridad"].rank(ascending=False, method="min").astype(int)
    )

    columnas_finales = [
        "clave", "localidad", "barrio",
        columna_poblacion,
        "pct_sedentarismo",
        "clases_por_semana", "escenarios_con_clases",
        "presupuesto_girado_millones", "pct_girado",
        "indice_prioridad", "ranking_prioridad",
    ]

    return df[columnas_finales].sort_values("ranking_prioridad")


# =====================================================================
# 6. GRAFICO
# =====================================================================

def graficar_top_barrios(resultado: pd.DataFrame, config: dict, ruta_png: Path, top_n: int = 15):
    """Genera un grafico de barras con los N barrios de mayor prioridad."""
    top = resultado.sort_values("ranking_prioridad").head(top_n)

    plt.figure(figsize=(10, 6))
    plt.barh(top["barrio"] + " (" + top["localidad"] + ")", top["indice_prioridad"])
    plt.gca().invert_yaxis()
    plt.xlabel("Indice de prioridad")
    plt.title(config["titulo"])
    plt.tight_layout()
    plt.savefig(ruta_png, dpi=150)
    plt.close()


# =====================================================================
# 7. EJECUCION PARA UNA CONFIGURACION
# =====================================================================

def ejecutar(config: dict):
    print(f"\nProcesando: {config['nombre']}")

    resultado = calcular_indice_prioridad(config)

    carpeta_salida = CARPETA_GENERADOS / config["carpeta"]
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    CARPETA_FIGURAS.mkdir(parents=True, exist_ok=True)

    # Los datos van a data/processed/; las figuras a outputs/figuras/.
    ruta_csv = carpeta_salida / config["salida_csv"]
    ruta_png = CARPETA_FIGURAS / config["salida_png"]

    resultado.to_csv(ruta_csv, index=False)
    graficar_top_barrios(resultado, config, ruta_png)

    print(f"  Filas: {len(resultado)}")
    print(f"  CSV guardado en: {ruta_csv}")
    print(f"  Grafico guardado en: {ruta_png}")
    print("\n  Top 5 barrios prioritarios:")
    print(
        resultado.head(5)[
            ["clave", "localidad", "barrio", "indice_prioridad", "ranking_prioridad"]
        ].to_string(index=False)
    )


# =====================================================================
# 8. MENU PRINCIPAL
# =====================================================================

def elegir_configuracion() -> str:
    print("Que poblacion deseas priorizar?")
    print("  1. Poblacion adulta")
    print("  2. Poblacion mayor")
    print("  3. Ambas")

    opcion = input("Elige una opcion (1/2/3): ").strip()

    if opcion not in {"1", "2", "3"}:
        print("Opcion invalida, se usara '3' (ambas) por defecto.")
        opcion = "3"

    return opcion


def main():
    opcion = elegir_configuracion()

    if opcion == "3":
        claves = ["1", "2"]
    else:
        claves = [opcion]

    for clave in claves:
        ejecutar(CONFIGURACIONES[clave])


if __name__ == "__main__":
    main()