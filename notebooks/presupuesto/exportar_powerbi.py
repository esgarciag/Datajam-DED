"""
Exporta las tablas de EJECUCIÓN PRESUPUESTAL en formato listo para Power BI.

Sale un modelo en estrella: dos dimensiones y cuatro tablas de hechos, todas
en formato largo y con las mismas llaves. Se cargan tal cual, sin transformar
nada en Power Query.

    python -m notebooks.presupuesto.exportar_powerbi

Salida en outputs/powerbi/
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .localidades import CODIGO_A_NOMBRE

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed" / "presupuesto"
SALIDA = ROOT / "outputs" / "powerbi"

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def escribir(df: pd.DataFrame, nombre: str) -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    # utf-8-sig para que Power BI y Excel respeten las tildes sin preguntar
    df.to_csv(SALIDA / f"{nombre}.csv", index=False, encoding="utf-8-sig")
    print(f"  {nombre + '.csv':38s} {len(df):>6,} filas × {len(df.columns)} col")


# Llave EXACTA del TopoJSON `bta_localidades` que ya usa el informe .pbix.
# La sacamos del archivo, no la inventamos: son mayúsculas sin tilde, salvo
# ANTONIO NARIÑO que sí lleva eñe, y La Candelaria que allá es solo
# "CANDELARIA". Sin esta columna el shapeMap no pinta.
NOMBRE_MAPA = {
    1: "USAQUEN", 2: "CHAPINERO", 3: "SANTA FE", 4: "SAN CRISTOBAL",
    5: "USME", 6: "TUNJUELITO", 7: "BOSA", 8: "KENNEDY", 9: "FONTIBON",
    10: "ENGATIVA", 11: "SUBA", 12: "BARRIOS UNIDOS", 13: "TEUSAQUILLO",
    14: "LOS MARTIRES", 15: "ANTONIO NARIÑO", 16: "PUENTE ARANDA",
    17: "CANDELARIA", 18: "RAFAEL URIBE URIBE", 19: "CIUDAD BOLIVAR",
    20: "SUMAPAZ",
}


def dim_localidad() -> pd.DataFrame:
    d = pd.DataFrame({
        "cod_localidad": list(CODIGO_A_NOMBRE),
        "localidad": list(CODIGO_A_NOMBRE.values()),
    })
    d["nombre_mapa"] = d["cod_localidad"].map(NOMBRE_MAPA)
    # CODIGO_LOC del TopoJSON viene como texto sin ceros a la izquierda
    d["codigo_loc"] = d["cod_localidad"].astype(str)

    pob = PROC / "poblacion_localidad_2025.csv"
    if pob.exists():
        p = pd.read_csv(pob)[["cod_localidad", "poblacion_total", "poblacion_60_mas"]]
        d = d.merge(p, on="cod_localidad", how="left")
    return d


def dim_calendario() -> pd.DataFrame:
    filas = []
    for anio in (2024, 2025, 2026, 2027):
        for mes in range(1, 13):
            filas.append({
                "periodo": anio * 100 + mes,
                "anio": anio,
                "mes": mes,
                "nombre_mes": MESES[mes - 1],
                "mes_abrev": MESES[mes - 1][:3],
                "trimestre": f"T{(mes - 1) // 3 + 1}",
                "es_ultimo_trimestre": mes >= 10,
                "es_diciembre": mes == 12,
                # Dónde debería ir el % ejecutado si se gastara parejo.
                # Va acá y no en los hechos: depende solo del mes.
                "ritmo_lineal_pct": round(100 * mes / 12, 2),
                "fecha": pd.Timestamp(anio, mes, 1),
            })
    return pd.DataFrame(filas)


def hechos_ejecucion_mensual() -> pd.DataFrame:
    """Serie mensual del IDRD y de los 20 Fondos de Desarrollo Local, unificada.

    `vigente` es un stock; `comprometido` y `girado` son acumulados dentro del
    año. `giro_mes` y `compromiso_mes` son los flujos ya diferenciados: son
    los que hay que usar para gráficos de barras mensuales.
    """
    partes = []

    idrd = PROC / "ejecucion_idrd_mensual.csv"
    if idrd.exists():
        d = pd.read_csv(idrd)
        d = d.assign(ambito="IDRD", cod_localidad=pd.NA, localidad="Distrital (IDRD)")
        partes.append(d)

    fdl = PROC / "ejecucion_fdl_mensual.csv"
    if fdl.exists():
        d = pd.read_csv(fdl).assign(ambito="Fondo de Desarrollo Local")
        partes.append(d)

    if not partes:
        return pd.DataFrame()

    m = pd.concat(partes, ignore_index=True)
    m["periodo"] = m["anio"] * 100 + m["mes"]

    # Nombres que avisan qué se puede sumar y qué no. Un `girado` a secas
    # invita a arrastrarlo a una suma; `girado_acumulado_anio` no.
    m = m.rename(columns={"ValorVigente": "vigente_snapshot",
                          "ValorCompromiso": "comprometido_acumulado_anio",
                          "ValorGiros": "girado_acumulado_anio"})
    # Llave del mapa, para que el shapeMap del informe pinte sin más pasos
    m["nombre_mapa"] = m["cod_localidad"].map(NOMBRE_MAPA)

    cols = ["ambito", "cod_localidad", "nombre_mapa", "localidad", "periodo",
            "anio", "mes", "vigente_snapshot", "comprometido_acumulado_anio",
            "girado_acumulado_anio", "giro_mes", "compromiso_mes"]
    return m[[c for c in cols if c in m.columns]].round(3)


def hechos_ejecucion_anual() -> pd.DataFrame:
    partes = []
    for archivo, ambito, loc in [
        ("ejecucion_idrd_anual.csv", "IDRD", "Distrital (IDRD)"),
        ("ejecucion_fdl_anual.csv", "Fondo de Desarrollo Local", None),
    ]:
        ruta = PROC / archivo
        if not ruta.exists():
            continue
        d = pd.read_csv(ruta).assign(ambito=ambito)
        if loc:
            d["cod_localidad"] = pd.NA
            d["localidad"] = loc
        partes.append(d)
    if not partes:
        return pd.DataFrame()

    a = pd.concat(partes, ignore_index=True)
    a["nombre_mapa"] = a["cod_localidad"].map(NOMBRE_MAPA)
    cols = ["ambito", "cod_localidad", "nombre_mapa", "localidad", "anio",
            "mes_corte", "vigente", "comprometido", "girado", "pct_comprometido",
            "pct_girado", "pct_girado_de_comprometido", "concentracion_diciembre",
            "concentracion_q4", "anio_completo"]
    return a[[c for c in cols if c in a.columns]].round(3)


def hechos_contratacion() -> pd.DataFrame:
    """Valor contratado por año, mes de inicio y tipo de objeto contractual."""
    ruta = PROC / "contratos_calendario_tipo.csv"
    if not ruta.exists():
        return pd.DataFrame()
    d = pd.read_csv(ruta)
    d["periodo"] = d["anio"] * 100 + d["mes"]
    d["nombre_mes"] = d["mes"].map(lambda m: MESES[int(m) - 1])
    return d[["periodo", "anio", "mes", "nombre_mes", "tipo_objeto",
              "valor_mm"]].round(2)


def hechos_contratacion_referencia() -> pd.DataFrame:
    """Línea base: el mismo calendario para tres ámbitos anidados.

    Permite poner la línea de "Todo el Distrito" encima de las barras y
    mostrar que contratar tarde es general, pero que estos proyectos lo hacen
    al triple.
    """
    ruta = PROC / "contratos_calendario_referencia.csv"
    if not ruta.exists():
        return pd.DataFrame()
    d = pd.read_csv(ruta)
    d["periodo"] = d["anio"] * 100 + d["mes"]
    d["nombre_mes"] = d["mes"].map(lambda m: MESES[int(m) - 1])
    return d[["ambito", "periodo", "anio", "mes", "nombre_mes",
              "valor_mm", "pct_del_anio"]].round(2)


def hechos_metas() -> pd.DataFrame:
    """Avance físico y financiero de cada actividad de los proyectos 8154/8155."""
    ruta = PROC / "desempeno_actividades_af.csv"
    if not ruta.exists():
        return pd.DataFrame()
    d = pd.read_csv(ruta).rename(columns={
        "proy": "cod_proyecto", "actividad": "actividad",
        "meta": "magnitud_programada", "entregado": "magnitud_entregada",
        "avance_fis": "avance_fisico_pct", "avance_fin": "avance_financiero_pct",
    })
    return d.round(2)


def tabla_referencias() -> pd.DataFrame:
    """Constantes del análisis, en una tabla en vez de repetidas por fila.

    Si cambia la fecha de corte, se cambia acá y no en 14 filas.
    """
    from .desempeno import AVANCE_TIEMPO

    return pd.DataFrame([
        {"referencia": "avance_tiempo_pct", "valor": round(AVANCE_TIEMPO, 1),
         "descripcion": "% del cuatrienio 2024-2027 transcurrido al corte 2025-09-30"},
        {"referencia": "ritmo_mensual_neutro_pct", "valor": 8.33,
         "descripcion": "% del giro anual que caería en un mes si se ejecutara parejo"},
    ])


def hechos_benchmark_proyectos() -> pd.DataFrame:
    """Los 264 proyectos del Distrito, para poder comparar sin escribir el
    número a mano en una caja de texto."""
    ruta = PROC / "desempeno_proyectos.csv"
    if not ruta.exists():
        return pd.DataFrame()
    d = pd.read_csv(ruta)
    d["es_actividad_fisica"] = d["CodigoProyecto"].isin([8154, 8155])
    d["es_idrd"] = d["entidad"].str.contains("Recreación y Deporte", na=False)
    cols = ["CodigoProyecto", "entidad", "proyecto", "programado_mm",
            "avance_fisico", "avance_financiero", "actividades",
            "actividades_en_cero", "es_actividad_fisica", "es_idrd"]
    return d[[c for c in cols if c in d.columns]].round(2)


def hechos_composicion() -> pd.DataFrame:
    """En qué se va la plata de los dos proyectos de actividad física."""
    ruta = PROC / "contratos_calendario_tipo.csv"
    if not ruta.exists():
        return pd.DataFrame()
    d = pd.read_csv(ruta)
    t = d.groupby(["anio", "tipo_objeto"])["valor_mm"].sum().reset_index()
    total = t.groupby("anio")["valor_mm"].transform("sum")
    t["pct_del_anio"] = (100 * t["valor_mm"] / total).round(1)
    return t.round(2)


def main() -> int:
    print("Exportando tablas para Power BI...\n")
    print("DIMENSIONES")
    escribir(dim_localidad(), "dim_localidad")
    escribir(dim_calendario(), "dim_calendario")
    escribir(tabla_referencias(), "referencias")

    print("\nHECHOS")
    for df, nombre in [
        (hechos_ejecucion_mensual(), "hechos_ejecucion_mensual"),
        (hechos_ejecucion_anual(), "hechos_ejecucion_anual"),
        (hechos_contratacion(), "hechos_contratacion"),
        (hechos_contratacion_referencia(), "hechos_contratacion_referencia"),
        (hechos_metas(), "hechos_metas"),
        (hechos_composicion(), "hechos_composicion_gasto"),
        (hechos_benchmark_proyectos(), "hechos_benchmark_proyectos"),
    ]:
        if len(df):
            escribir(df, nombre)
        else:
            print(f"  [falta la fuente de {nombre}]")

    print(f"\nTodo en: {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
