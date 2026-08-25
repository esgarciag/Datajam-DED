"""
Contratos del IDRD asociados a los proyectos de actividad física.

Responde dos preguntas:

1. ¿Se puede saber DÓNDE se ejecuta la plata? El dataset de contratos no trae
   campo de localidad —sólo `Ciudad = Bogotá`— así que lo único disponible es
   buscar menciones territoriales en el texto del objeto contractual. El
   resultado de esa búsqueda es en sí mismo un hallazgo y se reporta.

2. ¿CUÁNDO arranca la plata? `FechaInicioContrato` permite ver en qué mes
   empieza a ejecutarse cada peso contratado. Un programa de actividad física
   que arranca en noviembre no puede producir el efecto poblacional que
   promete su meta anual.

    python -m notebooks.presupuesto.contratos
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

from .localidades import CODIGO_A_NOMBRE, _ALIAS

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed" / "presupuesto"
TAB = ROOT / "outputs" / "tablas"

COMPRADOR_IDRD = "IDRD"
# BPIN de los dos proyectos de actividad física preventiva
BPIN_AF = {
    "2024110010252": "8154 · Bogotá Deportiva (iniciación a rendimiento)",
    "2024110010258": "8155 · Programas recreativos y actividad física",
}
MILLON = 1e6


def _slug(texto: str) -> str:
    s = unicodedata.normalize("NFKD", str(texto).lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9\s]", " ", s)


def localidades_mencionadas(texto: str) -> list[str]:
    s = _slug(texto)
    hits = {
        CODIGO_A_NOMBRE[cod]
        for alias, cod in _ALIAS.items()
        if re.search(rf"\b{re.escape(alias)}\b", s)
    }
    return sorted(hits)


def cargar_contratos_af() -> pd.DataFrame:
    usecols = [
        "AnioContrato", "CodigoContrato", "DescripcionContrato", "CodigoBPIN",
        "Contratista", "ValorPlaneado", "ValorContratado", "Comprador",
        "FechaInicioContrato", "FechaFinContrato",
    ]
    df = pd.read_csv(RAW / "contratos.csv", encoding="utf-8-sig",
                     usecols=usecols, low_memory=False)
    af = df[(df["Comprador"] == COMPRADOR_IDRD) & (df["CodigoBPIN"].isin(BPIN_AF))].copy()
    af["proyecto"] = af["CodigoBPIN"].map(BPIN_AF)

    # OJO: 268 contratos están cargados a los DOS proyectos a la vez, con el
    # mismo ValorContratado repetido en ambas filas (no es un reparto: es el
    # valor completo duplicado). Sumar sin deduplicar infla el total un 40,7%.
    antes = len(af)
    af = af.sort_values("CodigoBPIN").drop_duplicates(
        subset=["CodigoContrato", "AnioContrato", "ValorContratado"], keep="first"
    )
    if antes != len(af):
        print(f"[contratos] deduplicado: {antes} filas -> {len(af)} contratos únicos "
              f"({antes - len(af)} cargados a los dos BPIN)")

    af["valor_mm"] = pd.to_numeric(af["ValorContratado"], errors="coerce").fillna(0) / MILLON
    af["FechaInicioContrato"] = pd.to_datetime(af["FechaInicioContrato"], errors="coerce")
    af["mes_inicio"] = af["FechaInicioContrato"].dt.month
    return af


def trazabilidad_territorial(af: pd.DataFrame) -> pd.DataFrame:
    af = af.copy()
    af["localidades"] = af["DescripcionContrato"].fillna("").map(localidades_mencionadas)
    af["n_localidades"] = af["localidades"].map(len)
    con = af["n_localidades"] > 0
    return pd.DataFrame(
        [{
            "contratos_totales": len(af),
            "contratos_con_localidad": int(con.sum()),
            "pct_contratos_con_localidad": round(100 * con.mean(), 2),
            "valor_total_mm": round(af["valor_mm"].sum(), 1),
            "valor_con_localidad_mm": round(af.loc[con, "valor_mm"].sum(), 1),
            "pct_valor_con_localidad": round(100 * af.loc[con, "valor_mm"].sum()
                                             / af["valor_mm"].sum(), 2),
        }]
    )


# Objetos contractuales que son insumo o logística, no prestación del servicio
# de actividad física. Clasificación aproximada por palabra clave: sirve para
# dimensionar, no para cifrar. Los 10 contratos mayores son el 48,7% del valor
# y se pueden revisar a mano en veinte minutos.
PATRON_LOGISTICA = (
    r"tiquete|a[ée]re|alimentaci|refrigerio|uniforme|prendas|dotaci[oó]n|"
    r"licenciamien|software|plataforma|papeler|hotel|alojamien|transporte|"
    r"log[íi]stic|evento|certamen|premiaci|impres|publicidad|divulgaci"
)


def clasificar_objeto(af: pd.DataFrame) -> pd.DataFrame:
    af = af.copy()
    af["logistica"] = af["DescripcionContrato"].str.contains(
        PATRON_LOGISTICA, case=False, na=False, regex=True
    )
    af["tipo_objeto"] = af["logistica"].map(
        {True: "Viajes, comida, uniformes y eventos", False: "Todo lo demás"}
    )
    return af


def calendario_contratacion(af: pd.DataFrame) -> pd.DataFrame:
    t = af.pivot_table(index="mes_inicio", columns="AnioContrato",
                       values="valor_mm", aggfunc="sum")
    return t.reindex(range(1, 13))


def calendario_por_tipo(af: pd.DataFrame) -> pd.DataFrame:
    """Valor contratado por año, mes y tipo de objeto: formato largo."""
    af = clasificar_objeto(af)
    t = (
        af.groupby(["AnioContrato", "mes_inicio", "tipo_objeto"])["valor_mm"]
        .sum()
        .reset_index()
        .rename(columns={"AnioContrato": "anio", "mes_inicio": "mes"})
    )
    return t


def calendario_referencia() -> pd.DataFrame:
    """Línea base: ¿contratar en noviembre es raro, o lo hace todo el Distrito?

    Sin esta comparación, decir "el 49% arrancó en noviembre" es una
    insinuación: cualquiera puede responder que los cierres de año son
    estacionalmente tardíos en toda entidad pública. Con ella deja de serlo.

    Devuelve el % del valor anual contratado que arranca en cada mes, para
    tres ámbitos anidados.

    OJO con el orden: hay que deduplicar DENTRO de cada subconjunto. Si se
    deduplica el archivo completo antes de filtrar, los contratos cargados a
    varios proyectos se pierden y las cifras cambian.
    """
    usecols = ["Comprador", "CodigoBPIN", "AnioContrato", "ValorContratado",
               "FechaInicioContrato", "CodigoContrato"]
    c = pd.read_csv(RAW / "contratos.csv", encoding="utf-8-sig",
                    usecols=usecols, low_memory=False)
    c["mes"] = pd.to_datetime(c["FechaInicioContrato"], errors="coerce").dt.month
    c = c[c["mes"].notna() & c["AnioContrato"].isin([2024, 2025])]

    def dedup(d: pd.DataFrame) -> pd.DataFrame:
        return d.drop_duplicates(
            subset=["CodigoContrato", "AnioContrato", "ValorContratado"])

    ambitos = {
        "Proyectos de actividad física": dedup(
            c[(c["Comprador"] == COMPRADOR_IDRD) & (c["CodigoBPIN"].isin(BPIN_AF))]),
        "IDRD completo": dedup(c[c["Comprador"] == COMPRADOR_IDRD]),
        "Todo el Distrito": dedup(c),
    }

    filas = []
    for ambito, d in ambitos.items():
        for anio, g in d.groupby("AnioContrato"):
            total = g["ValorContratado"].sum()
            por_mes = g.groupby("mes")["ValorContratado"].sum()
            for mes in range(1, 13):
                filas.append({
                    "ambito": ambito,
                    "anio": int(anio),
                    "mes": mes,
                    "valor_mm": round(por_mes.get(mes, 0) / MILLON, 2),
                    "pct_del_anio": round(100 * por_mes.get(mes, 0) / total, 2),
                })
    return pd.DataFrame(filas)


def resumen_timing(af: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for anio, g in af.groupby("AnioContrato"):
        total = g["valor_mm"].sum()
        if total <= 0:
            continue
        filas.append({
            "anio": anio,
            "contratos": len(g),
            "valor_mm": round(total, 1),
            "pct_inicia_Q1": round(100 * g.loc[g["mes_inicio"] <= 3, "valor_mm"].sum() / total, 1),
            "pct_inicia_Q4": round(100 * g.loc[g["mes_inicio"] >= 10, "valor_mm"].sum() / total, 1),
            "mes_pico": int(g.groupby("mes_inicio")["valor_mm"].sum().idxmax()),
            "pct_en_mes_pico": round(
                100 * g.groupby("mes_inicio")["valor_mm"].sum().max() / total, 1),
        })
    return pd.DataFrame(filas)


def main() -> int:
    PROC.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)

    af = cargar_contratos_af()
    print(f"[contratos] contratos de actividad física IDRD: {len(af):,} · "
          f"${af['valor_mm'].sum():,.1f} millones")

    traz = trazabilidad_territorial(af)
    traz.to_csv(TAB / "trazabilidad_territorial_contratos.csv", index=False)
    print("\n=== ¿Se puede saber dónde se ejecuta? ===")
    print(traz.T.to_string(header=False))

    cal = calendario_contratacion(af)
    cal.to_csv(PROC / "contratos_calendario.csv", encoding="utf-8")
    print("\n=== Valor contratado por mes de inicio (millones COP) ===")
    print(cal.round(0).fillna(0).to_string())

    cal_tipo = calendario_por_tipo(af)
    cal_tipo.to_csv(PROC / "contratos_calendario_tipo.csv", index=False, encoding="utf-8")

    ref = calendario_referencia()
    ref.to_csv(PROC / "contratos_calendario_referencia.csv", index=False, encoding="utf-8")
    print("\n=== Línea base: % del valor anual que arranca en el último trimestre ===")
    q4 = (ref[ref["mes"] >= 10].groupby(["ambito", "anio"])["pct_del_anio"].sum()
          .unstack().round(1))
    print(q4.to_string())
    print("\n    Mes pico de cada ámbito:")
    for (amb, anio), g in ref.groupby(["ambito", "anio"]):
        pico = g.loc[g["pct_del_anio"].idxmax()]
        print(f"      {amb:32s} {anio}: mes {int(pico['mes']):2d} → {pico['pct_del_anio']:5.1f}%")

    cls = clasificar_objeto(af)
    resumen = cls.groupby("tipo_objeto").agg(
        contratos=("CodigoContrato", "size"), valor_mm=("valor_mm", "sum"))
    resumen["pct_valor"] = 100 * resumen["valor_mm"] / resumen["valor_mm"].sum()
    print("\n=== ¿En qué se va la plata? (clasificación aproximada) ===")
    print(resumen.round(1).to_string())
    top = cls.nlargest(10, "valor_mm")
    print(f"\nLos 10 contratos mayores = {100*top['valor_mm'].sum()/cls['valor_mm'].sum():.1f}% "
          f"del valor total, sobre {len(cls):,} contratos:")
    for _, r in top.iterrows():
        print(f"  ${r['valor_mm']:>9,.0f} mm  {int(r['AnioContrato'])}  "
              f"{str(r['DescripcionContrato'])[:74]}")

    tim = resumen_timing(af)
    tim.to_csv(PROC / "contratos_timing.csv", index=False, encoding="utf-8")
    print("\n=== Timing de la contratación ===")
    print(tim.to_string(index=False))

    # ¿El pico es un patrón general o unos pocos contratos grandes?
    print("\n=== Composición del mes pico de cada año ===")
    for _, r in tim.iterrows():
        g = af[(af["AnioContrato"] == r["anio"]) & (af["mes_inicio"] == r["mes_pico"])]
        if g.empty:
            continue
        top5 = g.nlargest(5, "valor_mm")["valor_mm"].sum()
        print(f"  {int(r['anio'])} mes {int(r['mes_pico'])}: {len(g)} contratos · "
              f"${g['valor_mm'].sum():,.0f} mm · "
              f"los 5 mayores concentran {100*top5/g['valor_mm'].sum():.1f}%")
        for _, x in g.nlargest(3, "valor_mm").iterrows():
            print(f"      ${x['valor_mm']:>9,.0f} mm  {str(x['DescripcionContrato'])[:72]}")

    af.drop(columns=["DescripcionContrato"]).to_csv(
        PROC / "contratos_af_idrd.csv", index=False, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
