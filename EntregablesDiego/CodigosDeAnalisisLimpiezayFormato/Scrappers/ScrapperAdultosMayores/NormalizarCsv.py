import pandas as pd
import unicodedata
from pathlib import Path


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

# Carpeta donde está este script:
# EntregablesDiego/CodigosdeAnalisisLimpiezasyFormato/
CARPETA_CODIGOS = Path(__file__).resolve().parent

# Carpeta principal:
# EntregablesDiego/
CARPETA_PROYECTO = CARPETA_CODIGOS.parent

# CSV generados por el scraper
CARPETA_POBLACION_MAYOR = (
    CARPETA_PROYECTO
    / "CSVUsados"
    / "Generados"
    / "PoblacionMayor"
)

# Crear la carpeta si no existe
CARPETA_POBLACION_MAYOR.mkdir(parents=True, exist_ok=True)


# ============================================================
# ARCHIVOS
# ============================================================

ARCHIVO_ENTRADA = (
    CARPETA_POBLACION_MAYOR
    / "personas_Mayores_por_barrio_resumen.csv"
)

ARCHIVO_SALIDA = (
    CARPETA_POBLACION_MAYOR
    / "PoblacionMayorBarrioNormalizado.csv"
)


# ============================================================
# FUNCIONES
# ============================================================

def normalizar(texto):
    """Convierte a mayúsculas y elimina tildes/acentos."""
    if pd.isna(texto):
        return texto

    texto = str(texto).upper()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(
        c for c in texto
        if not unicodedata.combining(c)
    )

    return texto


def convertir(
    input_path,
    output_path,
    sep_entrada=',',
    sep_salida='\t'
):
    # El archivo de origen trae la columna
    # "total_personas_mayores" duplicada.
    #
    # Pandas la renombra automáticamente a:
    # total_personas_mayores
    # total_personas_mayores.1

    df = pd.read_csv(
        input_path,
        sep=sep_entrada
    )

    columnas = list(df.columns)

    col_valor = columnas[2]

    col_valor_raw = (
        columnas[3]
        if len(columnas) > 3
        else columnas[2]
    )

    df = df.rename(columns={
        columnas[0]: 'localidad',
        columnas[1]: 'barrio',
        col_valor: 'total_personas_mayores',
    })

    df['total_personas_mayores'] = pd.to_numeric(
        df['total_personas_mayores'],
        errors='coerce'
    )

    # En este origen el valor raw es igual al valor.
    df['total_personas_mayores_raw'] = (
        df[col_valor_raw]
        if col_valor_raw != col_valor
        else df['total_personas_mayores']
    )

    df['total_personas_mayores_raw'] = pd.to_numeric(
        df['total_personas_mayores_raw'],
        errors='coerce'
    ).astype('Int64')

    # Normalización
    df['barrio_norm'] = df['barrio'].apply(normalizar)
    df['localidad_norm'] = df['localidad'].apply(normalizar)

    # Clave localidad + barrio
    df['clave'] = (
        df['localidad_norm']
        + '_'
        + df['barrio_norm']
    )

    columnas_finales = [
        'localidad',
        'barrio',
        'total_personas_mayores',
        'total_personas_mayores_raw',
        'barrio_norm',
        'localidad_norm',
        'clave'
    ]

    df = df[columnas_finales]

    df.to_csv(
        output_path,
        sep=sep_salida,
        index=False
    )

    print(f"Listo: {output_path}")

    return df


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    if not ARCHIVO_ENTRADA.exists():
        print("ERROR: No se encontró el archivo de entrada:")
        print(ARCHIVO_ENTRADA)
        print()
        print("Asegúrate de que el scraper haya generado:")
        print("personas_Mayores_por_barrio_resumen.csv")
        raise FileNotFoundError(ARCHIVO_ENTRADA)

    convertir(
        input_path=ARCHIVO_ENTRADA,
        output_path=ARCHIVO_SALIDA
    )