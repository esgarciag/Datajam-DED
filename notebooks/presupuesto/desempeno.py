"""
¿Qué tan bien se está haciendo? — avance físico, no solo plata.

Hasta acá medimos DÓNDE va el esfuerzo. Esto mide si el esfuerzo produce lo
que prometió. Son preguntas distintas y se confunden todo el tiempo: una
entidad puede girar el 100% del presupuesto y entregar la mitad de las metas.

Tres medidas, y la comparación entre ellas es lo que importa:

  avance de tiempo : cuánto del cuatrienio ya transcurrió (referencia neutra)
  avance físico    : magnitud entregada / magnitud programada
  avance financiero: valor girado / valor programado

Si el avance físico va muy por debajo del avance de tiempo, el proyecto está
atrasado. Si el avance físico va por debajo del financiero, se está pagando
más rápido de lo que se entrega.

Advertencia sobre la fuente: las "magnitudes" las reporta la propia entidad y
no hay verificación independiente. Miden lo que la entidad dice que entregó.

    python -m notebooks.presupuesto.desempeno
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed" / "presupuesto"

IDRD = "Instituto Distrital de Recreación y Deporte"
PROYECTOS_AF = [8154, 8155]

# El PDD va de 2024 a 2027; el corte de la fuente es 2025-09-30.
INICIO, FIN, CORTE = pd.Timestamp("2024-01-01"), pd.Timestamp("2027-12-31"), pd.Timestamp("2025-09-30")
AVANCE_TIEMPO = 100 * (CORTE - INICIO).days / (FIN - INICIO).days


def cargar() -> pd.DataFrame:
    df = pd.read_csv(RAW / "proyectos_inversion.csv", encoding="utf-8-sig", low_memory=False)
    # Grano fino: una fila por proyecto × meta × actividad
    g = df.drop_duplicates(subset=["CodigoProyecto", "PlanMetaProductoId", "ActividadCodigo"]).copy()
    g = g[g["ActividadMagnitudProgramadaTotal"] > 0].copy()

    g["avance_fisico"] = (
        100 * g["ActividadMagnitudEntregadoTotal"] / g["ActividadMagnitudProgramadaTotal"]
    ).clip(upper=300)
    g["avance_financiero"] = (
        100 * g["ActividadValorGiradoTotal"]
        / g["ActividadValorProgramadoTotal"].replace(0, pd.NA)
    ).clip(upper=300)
    return g


def por_proyecto(g: pd.DataFrame) -> pd.DataFrame:
    """Pondera cada actividad por la plata que maneja, no por conteo simple."""
    def agg(x: pd.DataFrame) -> pd.Series:
        w = x["ActividadValorProgramadoTotal"]
        w = w if w.sum() > 0 else pd.Series(1.0, index=x.index)
        return pd.Series({
            "entidad": x["Entidad"].iloc[0],
            "proyecto": x["NombreProyecto"].iloc[0][:58],
            "actividades": len(x),
            "programado_mm": x["ActividadValorProgramadoTotal"].sum(),
            "avance_fisico": (x["avance_fisico"] * w).sum() / w.sum(),
            "avance_financiero": (x["avance_financiero"].fillna(0) * w).sum() / w.sum(),
            "actividades_en_cero": int((x["avance_fisico"] == 0).sum()),
        })

    out = g.groupby("CodigoProyecto").apply(agg, include_groups=False).reset_index()
    out["brecha_vs_tiempo"] = out["avance_fisico"] - AVANCE_TIEMPO
    return out


def main() -> int:
    PROC.mkdir(parents=True, exist_ok=True)
    g = cargar()
    print(f"[desempeno] corte de la fuente: {CORTE.date()} · "
          f"transcurrido del cuatrienio: {AVANCE_TIEMPO:.1f}%")

    p = por_proyecto(g)
    p.to_csv(PROC / "desempeno_proyectos.csv", index=False, encoding="utf-8")

    af = p[p["CodigoProyecto"].isin(PROYECTOS_AF)]
    idrd = p[p["entidad"] == IDRD]
    print("\n=== Los dos proyectos de actividad física ===")
    cols = ["CodigoProyecto", "avance_fisico", "avance_financiero",
            "brecha_vs_tiempo", "actividades", "actividades_en_cero", "programado_mm"]
    print(af[cols].round(1).to_string(index=False))

    print("\n=== Contra qué compararlo ===")
    for etiqueta, sub in [("Los 2 de actividad física", af),
                          (f"Todos los del IDRD ({len(idrd)})", idrd),
                          (f"Todo el Distrito ({len(p)})", p)]:
        w = sub["programado_mm"]
        print(f"  {etiqueta:32s} físico {(sub['avance_fisico']*w).sum()/w.sum():5.1f}%  "
              f"financiero {(sub['avance_financiero']*w).sum()/w.sum():5.1f}%")
    print(f"  {'Referencia: tiempo transcurrido':32s} {AVANCE_TIEMPO:19.1f}%")

    print("\n=== Actividades de 8154/8155, una por una ===")
    det = g[g["CodigoProyecto"].isin(PROYECTOS_AF)].sort_values("avance_fisico")
    det = det[["CodigoProyecto", "ActividadNombre", "ActividadMagnitudProgramadaTotal",
               "ActividadMagnitudEntregadoTotal", "avance_fisico", "avance_financiero"]]
    det.columns = ["proy", "actividad", "meta", "entregado", "avance_fis", "avance_fin"]
    det["actividad"] = det["actividad"].str[:62]
    print(det.round(1).to_string(index=False))
    det.to_csv(PROC / "desempeno_actividades_af.csv", index=False, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
