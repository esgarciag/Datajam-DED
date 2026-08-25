"""
Calidad de la ejecución presupuestal, a partir del Presupuesto General del
Distrito (Secretaría Distrital de Hacienda), que viene con corte MENSUAL.

Esta es la fuente clave del proyecto y conviene entender su forma:

- `Periodo` es YYYYMM. Hay 29 cortes: 2024-01 a 2026-05.
- `ValorVigente` es un STOCK: el presupuesto aprobado a esa fecha.
- `ValorCompromiso` y `ValorGiros` son ACUMULADOS dentro del año: crecen mes a
  mes y se reinician en enero. Para obtener el flujo de cada mes hay que
  diferenciar dentro de cada año.

Con eso se calculan tres cosas distintas que la gente suele confundir:

1. `pct_comprometido` = comprometido / vigente al cierre.
   Mide si la entidad logró CONTRATAR la plata. Bajo => problema de gestión
   contractual o de planeación.
2. `pct_girado` = girado / vigente al cierre.
   Mide si la plata efectivamente SALIÓ. Bajo con comprometido alto => el
   dinero está amarrado en contratos que no se han pagado.
3. `concentracion_diciembre` = giros de diciembre / giros del año.
   Mide si el gasto se ejecuta a lo largo del año o se apura al final. Un
   valor alto es la firma de la ejecución tardía, aunque el % anual se vea
   bien. Referencia neutra: 1/12 = 8,3%.

    python -m notebooks.presupuesto.ejecucion
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .localidades import normalizar

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed" / "presupuesto"

IDRD = "Instituto Distrital de Recreación y Deporte"
MILLON = 1e6


def cargar_presupuesto() -> pd.DataFrame:
    df = pd.read_csv(RAW / "presupuesto_general.csv", encoding="utf-8-sig",
                     low_memory=False)
    df["anio"] = df["Periodo"] // 100
    df["mes"] = df["Periodo"] % 100
    for c in ("ValorVigente", "ValorCompromiso", "ValorGiros"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0) / MILLON
    return df


def serie_mensual(df: pd.DataFrame, llaves: list[str]) -> pd.DataFrame:
    """Agrega por llaves + año + mes y convierte acumulados en flujos."""
    agg = (
        df.groupby(llaves + ["anio", "mes"])[
            ["ValorVigente", "ValorCompromiso", "ValorGiros"]
        ]
        .sum()
        .reset_index()
        .sort_values(llaves + ["anio", "mes"])
    )
    g = agg.groupby(llaves + ["anio"], sort=False)
    agg["giro_mes"] = g["ValorGiros"].diff().fillna(agg["ValorGiros"])
    agg["compromiso_mes"] = g["ValorCompromiso"].diff().fillna(agg["ValorCompromiso"])
    return agg


def indicadores_anuales(mensual: pd.DataFrame, llaves: list[str]) -> pd.DataFrame:
    """Cierre de cada año + indicadores de calidad de ejecución."""
    idx = mensual.groupby(llaves + ["anio"])["mes"].transform("max") == mensual["mes"]
    cierre = mensual[idx].copy()

    dic = (
        mensual[mensual["mes"] == 12]
        .set_index(llaves + ["anio"])["giro_mes"]
        .rename("giro_diciembre")
    )
    q4 = (
        mensual[mensual["mes"] >= 10]
        .groupby(llaves + ["anio"])["giro_mes"]
        .sum()
        .rename("giro_q4")
    )
    cierre = cierre.join(dic, on=llaves + ["anio"]).join(q4, on=llaves + ["anio"])

    cierre["pct_comprometido"] = 100 * cierre["ValorCompromiso"] / cierre["ValorVigente"]
    cierre["pct_girado"] = 100 * cierre["ValorGiros"] / cierre["ValorVigente"]
    cierre["pct_girado_de_comprometido"] = (
        100 * cierre["ValorGiros"] / cierre["ValorCompromiso"].replace(0, pd.NA)
    )
    cierre["concentracion_diciembre"] = (
        100 * cierre["giro_diciembre"] / cierre["ValorGiros"].replace(0, pd.NA)
    )
    cierre["concentracion_q4"] = (
        100 * cierre["giro_q4"] / cierre["ValorGiros"].replace(0, pd.NA)
    )
    cierre["anio_completo"] = cierre["mes"] == 12
    return cierre.rename(
        columns={"ValorVigente": "vigente", "ValorCompromiso": "comprometido",
                 "ValorGiros": "girado", "mes": "mes_corte"}
    )


def ejecucion_idrd(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    idrd = df[(df["Institucion"] == IDRD) & (df["Finalidad"] == "Inversión")]
    mensual = serie_mensual(idrd, ["Institucion"])
    return mensual, indicadores_anuales(mensual, ["Institucion"])


def ejecucion_fdl(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fondos de Desarrollo Local -> una serie por localidad."""
    fdl = df[
        (df["TipoPresupuesto"] == "Presupuesto de los Fondos de Desarrollo Local")
        & (df["Finalidad"] == "Inversión")
    ].copy()
    loc = normalizar(fdl["Institucion"].str.replace("Fondo de Desarrollo Local de ",
                                                    "", regex=False))
    fdl["cod_localidad"] = loc["cod_localidad"]
    fdl["localidad"] = loc["localidad"]

    sin_mapear = fdl[fdl["cod_localidad"].isna()]["Institucion"].unique()
    if len(sin_mapear):
        raise ValueError(f"FDL sin localidad: {sin_mapear}")

    mensual = serie_mensual(fdl, ["cod_localidad", "localidad"])
    return mensual, indicadores_anuales(mensual, ["cod_localidad", "localidad"])


def main() -> int:
    PROC.mkdir(parents=True, exist_ok=True)
    df = cargar_presupuesto()
    print(f"[ejecucion] cortes disponibles: {df['Periodo'].min()} a {df['Periodo'].max()}")

    m_idrd, a_idrd = ejecucion_idrd(df)
    m_idrd.to_csv(PROC / "ejecucion_idrd_mensual.csv", index=False, encoding="utf-8")
    a_idrd.to_csv(PROC / "ejecucion_idrd_anual.csv", index=False, encoding="utf-8")

    print("\n=== IDRD — inversión, cierre de cada vigencia (millones COP) ===")
    cols = ["anio", "mes_corte", "vigente", "comprometido", "girado",
            "pct_comprometido", "pct_girado", "concentracion_diciembre"]
    print(a_idrd[cols].round(1).to_string(index=False))

    m_fdl, a_fdl = ejecucion_fdl(df)
    m_fdl.to_csv(PROC / "ejecucion_fdl_mensual.csv", index=False, encoding="utf-8")
    a_fdl.to_csv(PROC / "ejecucion_fdl_anual.csv", index=False, encoding="utf-8")

    print("\n=== Fondos de Desarrollo Local — vigencia 2025 cerrada ===")
    v = a_fdl[a_fdl["anio"] == 2025].sort_values("pct_girado")
    cols = ["localidad", "vigente", "comprometido", "girado", "pct_comprometido",
            "pct_girado", "concentracion_diciembre"]
    print(v[cols].round(1).to_string(index=False))

    print("\n=== Cuánto del giro anual cae en diciembre (referencia neutra: 8,3%) ===")
    for anio in (2024, 2025):
        sub = a_fdl[a_fdl["anio"] == anio]
        print(f"  {anio}: mediana FDL {sub['concentracion_diciembre'].median():.1f}%  "
              f"| máx {sub['concentracion_diciembre'].max():.1f}% "
              f"({sub.loc[sub['concentracion_diciembre'].idxmax(), 'localidad']})")
        i = a_idrd[a_idrd["anio"] == anio]
        if len(i):
            print(f"        IDRD {i['concentracion_diciembre'].iloc[0]:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
