"""
Las seis figuras de la página "¿Se está ejecutando bien el presupuesto?".

Dos son nuevas (el embudo y la concentración en diciembre) y cuatro se copian
de las ya verificadas, renumeradas en el orden narrativo de la página.

    python -m notebooks.presupuesto.viz_ejecucion

Salida en outputs/figuras_ejecucion/
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .viz import (AZUL, AZUL_CLARO, GRIS, GRIS_TENUE, ROJO, TINTA,
                  aplicar_estilo, pie_de_fuente)

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed" / "presupuesto"
ORIGEN = ROOT / "outputs" / "figuras"
SALIDA = ROOT / "outputs" / "figuras_ejecucion"

MESES = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]


def guardar(fig: plt.Figure, nombre: str) -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(SALIDA / f"{nombre}.{ext}")
    plt.close(fig)
    print(f"  nueva   {nombre}.png|svg")


def fig_embudo() -> None:
    """Afirmación 1: se compromete casi todo y se gira dos tercios."""
    ruta = PROC / "ejecucion_idrd_anual.csv"
    if not ruta.exists():
        print("  (falta ejecucion_idrd_anual.csv)")
        return
    d = pd.read_csv(ruta)
    d = d[d["anio_completo"]].sort_values("anio")
    if d.empty:
        return

    fig, axes = plt.subplots(1, len(d), figsize=(10.5, 5.2), sharey=True)
    if len(d) == 1:
        axes = [axes]

    etapas = ["Presupuesto\nvigente", "Comprometido\n(contratado)", "Girado\n(pagado)"]
    colores = [GRIS_TENUE, AZUL_CLARO, ROJO]

    for ax, (_, r) in zip(axes, d.iterrows()):
        vals = [r["vigente"], r["comprometido"], r["girado"]]
        pcts = [100, r["pct_comprometido"], r["pct_girado"]]
        y = [2, 1, 0]

        ax.barh(y, vals, height=0.62, color=colores)
        for yi, v, p in zip(y, vals, pcts):
            ax.text(v + r["vigente"] * 0.02, yi, f"{p:.0f}%", va="center",
                    fontsize=11.5, fontweight="bold", color=TINTA)

        ax.set_yticks(y)
        ax.set_yticklabels(etapas, fontsize=9.5)
        ax.set_xlim(0, r["vigente"] * 1.22)
        ax.set_title(f"{int(r['anio'])}", loc="left", fontsize=12)
        ax.set_xlabel("Millones de pesos")
        ax.grid(axis="y", visible=False)

    fig.suptitle(
        "Se contrata casi todo el presupuesto. Se paga dos tercios.",
        x=0.007, y=1.03, ha="left", va="top", fontsize=13.5, fontweight="bold",
    )
    pie_de_fuente(
        fig,
        "IDRD, inversión. Presupuesto General del Distrito — Secretaría Distrital "
        "de Hacienda, cierre de cada vigencia.",
    )
    guardar(fig, "ejecucion_2_embudo")


def fig_diciembre() -> None:
    """Afirmación 3: diciembre concentra el gasto."""
    ruta = PROC / "ejecucion_idrd_mensual.csv"
    if not ruta.exists():
        print("  (falta ejecucion_idrd_mensual.csv)")
        return
    m = pd.read_csv(ruta)
    anios = [a for a in (2024, 2025) if a in set(m["anio"])]

    fig, axes = plt.subplots(1, len(anios), figsize=(10.5, 4.8), sharey=True)
    if len(anios) == 1:
        axes = [axes]

    for ax, anio in zip(axes, anios):
        g = m[m["anio"] == anio].sort_values("mes")
        total = g["giro_mes"].sum()
        pct = 100 * g["giro_mes"] / total
        colores = [ROJO if mes == 12 else AZUL_CLARO for mes in g["mes"]]

        ax.bar(g["mes"], pct, color=colores, width=0.72)
        ax.axhline(100 / 12, color=TINTA, ls="--", lw=1.1)

        dic = pct[g["mes"] == 12]
        if len(dic):
            ax.text(12, dic.iloc[0] + 0.7, f"{dic.iloc[0]:.0f}%", ha="center",
                    fontsize=11, fontweight="bold", color=ROJO)

        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(MESES)
        ax.set_title(f"{anio}", loc="left", fontsize=12)

    axes[0].set_ylabel("% del giro del año")
    axes[0].text(0.9, 100 / 12 + 0.5, "reparto parejo: 8,3%", fontsize=8.6,
                 color=TINTA, va="bottom")

    fig.suptitle(
        "Uno de cada cinco pesos del año se paga en diciembre",
        x=0.007, y=1.03, ha="left", va="top", fontsize=13.5, fontweight="bold",
    )
    pie_de_fuente(
        fig,
        "IDRD, inversión. Giro mensual como porcentaje del giro anual. "
        "Presupuesto General del Distrito — Secretaría Distrital de Hacienda.",
    )
    guardar(fig, "ejecucion_3_diciembre")


def fig_contratacion_con_base() -> None:
    """Afirmación 1, con la línea base del Distrito.

    Sin comparación, "el 49% arrancó en noviembre" es desestimable: cualquiera
    responde que los cierres de año son tardíos en toda entidad pública. La
    línea del Distrito convierte la insinuación en un dato contra una norma.
    """
    ruta_tipo = PROC / "contratos_calendario_tipo.csv"
    ruta_ref = PROC / "contratos_calendario_referencia.csv"
    if not (ruta_tipo.exists() and ruta_ref.exists()):
        print("  (falta calendario o referencia — corré python -m notebooks.presupuesto.contratos)")
        return

    tipo = pd.read_csv(ruta_tipo)
    ref = pd.read_csv(ruta_ref)
    anios = [a for a in (2024, 2025) if a in set(tipo["anio"])]
    etq_log = "Viajes, comida, uniformes y eventos"

    fig, axes = plt.subplots(1, len(anios), figsize=(11, 5.2), sharey=True)
    if len(anios) == 1:
        axes = [axes]

    for ax, anio in zip(axes, anios):
        g = tipo[tipo["anio"] == anio]
        total = g["valor_mm"].sum()
        log = (g[g["tipo_objeto"] == etq_log].set_index("mes")["valor_mm"]
               .reindex(range(1, 13)).fillna(0) * 100 / total)
        res = (g[g["tipo_objeto"] == "Todo lo demás"].set_index("mes")["valor_mm"]
               .reindex(range(1, 13)).fillna(0) * 100 / total)

        ax.bar(range(1, 13), res, color=AZUL_CLARO, width=0.74,
               label="Todo lo demás")
        ax.bar(range(1, 13), log, bottom=res, color=ROJO, width=0.74,
               label=etq_log)

        base = (ref[(ref["ambito"] == "Todo el Distrito") & (ref["anio"] == anio)]
                .set_index("mes")["pct_del_anio"].reindex(range(1, 13)).fillna(0))
        ax.plot(range(1, 13), base, color=TINTA, lw=1.8, ls="--", marker="o",
                ms=4, zorder=5, label="Todo el Distrito (referencia)")

        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(MESES)
        ax.set_title(f"{anio}", loc="left", fontsize=12)

    axes[0].set_ylabel("% del valor contratado del año")
    axes[0].legend(loc="upper left", fontsize=8.6)
    fig.suptitle(
        "Todo el Distrito contrata tarde. Estos proyectos, al triple.\n"
        "En noviembre de 2024 el Distrito concentró el 18% del valor del año; "
        "los proyectos de actividad física, el 49%.",
        x=0.007, y=1.10, ha="left", va="top", fontsize=13, fontweight="bold",
    )
    pie_de_fuente(
        fig,
        "Contratos del Distrito (SECOP), por mes de inicio del contrato. "
        "Barras: proyectos de actividad física del IDRD (BPIN 2024110010252 y "
        "2024110010258), deduplicados.\nLínea: todos los contratos del Distrito "
        "con fecha de inicio en el mismo año. Corte 2026-05-07.",
    )
    guardar(fig, "ejecucion_1_contratos_fin_de_ano")


# Figuras ya verificadas que se reusan, en orden narrativo
COPIAS = {
    "04_curva_ejecucion_idrd": "respaldo_curva_mensual_acumulada",
    "06_ejecucion_fdl": "ejecucion_4_localidades",
    "12_avance_fisico": "ejecucion_5_metas",
    "10_curvas_concentracion": "ejecucion_6_degradacion",
}


def copiar_existentes() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    for origen, destino in COPIAS.items():
        faltan = []
        for ext in ("png", "svg"):
            o = ORIGEN / f"{origen}.{ext}"
            if o.exists():
                shutil.copy2(o, SALIDA / f"{destino}.{ext}")
            else:
                faltan.append(ext)
        if faltan:
            print(f"  [falta] {origen}.{'/'.join(faltan)} — corré python -m notebooks.presupuesto.viz")
        else:
            print(f"  copiada {destino}.png|svg")


def main() -> int:
    aplicar_estilo()
    print("Figuras de la página de ejecución presupuestal\n")
    fig_contratacion_con_base()
    fig_embudo()
    fig_diciembre()
    copiar_existentes()

    print(f"\nSeis figuras en: {SALIDA}")
    print("""
Orden narrativo:
  1  contratos_fin_de_ano   Todo el Distrito contrata tarde; estos, al triple
  2  embudo                 Se contrata el 96%, se paga el 64%
  3  diciembre              Uno de cada cinco pesos se paga en diciembre
  4  localidades            El rezago del pago es de todo el Distrito
  5  metas                  Ninguna meta va al ritmo que debería
  6  degradacion            El esfuerzo se degrada en cada paso

Frase de cierre, apuntando a la sección del mapa:
  "Este presupuesto que se gira tarde y desigual es el que debería sostener
   las clases que en 8 localidades no existen."

Aparte, sin numerar:
  respaldo_curva_mensual_acumulada  — solo si preguntan por el detalle mensual""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
