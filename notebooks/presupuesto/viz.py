"""
Estilo común y figuras del proyecto.

    python -m notebooks.presupuesto.viz            # regenera todas las figuras disponibles

Las figuras se escriben en outputs/figuras/ en PNG (300 dpi) y SVG.
El SVG sirve para meterlo en el informe o en las diapositivas sin que pixele.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed" / "presupuesto"
FIG = ROOT / "outputs" / "figuras"

# Paleta: rojo = riesgo alto, azul = riesgo bajo, gris = referencia
ROJO = "#b2182b"
ROJO_CLARO = "#ef8a62"
AZUL = "#2166ac"
AZUL_CLARO = "#67a9cf"
GRIS = "#8c8c8c"
GRIS_TENUE = "#d9d9d9"
TINTA = "#1a1a1a"


def aplicar_estilo() -> None:
    mpl.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.edgecolor": GRIS,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRIS_TENUE,
            "grid.linewidth": 0.6,
            "xtick.color": TINTA,
            "ytick.color": TINTA,
            "text.color": TINTA,
            "legend.frameon": False,
        }
    )


def guardar(fig: plt.Figure, nombre: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"{nombre}.{ext}")
    plt.close(fig)
    print(f"  figura -> outputs/figuras/{nombre}.png|svg")


def pie_de_fuente(fig: plt.Figure, texto: str) -> None:
    fig.text(0.01, -0.02, texto, fontsize=7.5, color=GRIS, ha="left", va="top")


# --------------------------------------------------------------------------
# Figura 1 — Dumbbell: inactividad física 2017 vs 2021
# --------------------------------------------------------------------------
def fig_dumbbell_inactividad(riesgo: pd.DataFrame) -> None:
    d = riesgo.sort_values("nada_2021")
    y = range(len(d))

    fig, ax = plt.subplots(figsize=(9, 7.5))
    for i, (_, r) in enumerate(d.iterrows()):
        ax.plot([r["nada_2017"], r["nada_2021"]], [i, i],
                color=GRIS_TENUE, lw=2.6, zorder=1, solid_capstyle="round")
    ax.scatter(d["nada_2017"], y, s=42, color=GRIS, zorder=2)
    ax.scatter(d["nada_2021"], y, s=62, color=AZUL, zorder=3)

    from matplotlib.lines import Line2D

    ax.legend(
        handles=[
            Line2D([], [], marker="o", ls="", color=GRIS, markersize=7, label="2017"),
            Line2D([], [], marker="o", ls="", color=AZUL, markersize=7, label="2021"),
        ],
        loc="lower right", fontsize=9,
    )

    ax.axvline(49.7, color=TINTA, ls="--", lw=1, zorder=0)
    ax.text(49.9, len(d) - 0.4, "Bogotá 49,7%", fontsize=8, color=TINTA)

    ax.set_yticks(list(y))
    ax.set_yticklabels(d["localidad"])
    ax.set_xlabel("% que no practicó deporte ni actividad física en el mes")
    ax.set_title("Inactividad física por localidad, 2017 y 2021", loc="left")
    ax.set_xlim(25, 65)
    pie_de_fuente(
        fig,
        "Secretaría Distrital de Salud — Observatorio de Salud de Bogotá "
        "(Encuesta Multipropósito 2017 y 2021).",
    )
    guardar(fig, "01_inactividad_2017_2021")


# --------------------------------------------------------------------------
# Figura 2 — Índice de riesgo descompuesto
# --------------------------------------------------------------------------
def fig_indice_riesgo(riesgo: pd.DataFrame) -> None:
    d = riesgo.sort_values("indice_riesgo")
    y = range(len(d))

    fig, ax = plt.subplots(figsize=(9, 7.5))
    izq = pd.Series(0.0, index=d.index)
    partes = [
        ("c_nivel", 0.45, ROJO, "Cuánta gente no hace nada de ejercicio"),
        ("c_deficit", 0.35, ROJO_CLARO, "Qué tan poca gente hace ejercicio 3+ veces/semana"),
        ("c_deterioro", 0.20, AZUL_CLARO, "Cuánto empeoró entre 2017 y 2021"),
    ]
    for col, peso, color, etiqueta in partes:
        ancho = d[col] * peso
        ax.barh(list(y), ancho, left=izq, color=color, height=0.72, label=etiqueta)
        izq = izq + ancho

    ax.set_yticks(list(y))
    ax.set_yticklabels(d["localidad"])
    ax.set_xlabel("Índice de riesgo  (0 = la mejor de la ciudad · 100 = la peor)")
    ax.set_title(
        "Qué hay detrás del riesgo de cada localidad",
        loc="left",
    )
    ax.legend(loc="lower right", fontsize=8.5)
    pie_de_fuente(
        fig,
        "Elaboración propia a partir de datos de la Secretaría Distrital de Salud. "
        "Cada localidad se compara contra las otras 19; los tres pedazos pesan 45%, 35% y 20%.",
    )
    guardar(fig, "02_indice_riesgo")


# --------------------------------------------------------------------------
# Figura 3 — Mapa de las dos dimensiones
# --------------------------------------------------------------------------
def fig_dispersion_riesgo(riesgo: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 7))
    x, y = riesgo["nada_2021"], riesgo["3omas_sem_2021"]

    mx, my = 49.7, 20.4  # referencia Bogotá 2021
    ax.axvline(mx, color=GRIS, ls="--", lw=1)
    ax.axhline(my, color=GRIS, ls="--", lw=1)

    ax.scatter(
        x, y, s=110, color=AZUL,
        edgecolor="white", linewidth=1.1, zorder=3,
    )
    etiquetas = [
        ax.text(r["nada_2021"], r["3omas_sem_2021"], r["localidad"],
                fontsize=8, color=TINTA)
        for _, r in riesgo.iterrows()
    ]
    try:  # separa etiquetas superpuestas si adjustText está instalado
        from adjustText import adjust_text

        adjust_text(
            etiquetas, ax=ax,
            expand=(1.15, 1.35),
            arrowprops=dict(arrowstyle="-", color=GRIS, lw=0.6),
        )
    except ImportError:
        print("  (opcional: pip install adjustText para separar las etiquetas)")

    ax.set_xlabel("% que no hizo ninguna actividad física (2021)")
    ax.set_ylabel("% que hace actividad física 3+ veces/semana (2021)")
    ax.set_title(
        "Inactividad y práctica regular por localidad, 2021\n"
        "Las líneas marcan el promedio de Bogotá",
        loc="left",
    )
    ax.set_xlim(29, 59)
    ax.set_ylim(7, 37)
    pie_de_fuente(fig, "Secretaría Distrital de Salud — Observatorio de Salud de Bogotá (2021).")
    guardar(fig, "03_dispersion_riesgo")


# --------------------------------------------------------------------------
# Figura 4 — Curva de ejecución mensual del IDRD
# --------------------------------------------------------------------------
def fig_curva_ejecucion_idrd() -> None:
    ruta = PROC / "ejecucion_idrd_mensual.csv"
    if not ruta.exists():
        print("  (falta ejecucion_idrd_mensual.csv — corré python -m notebooks.presupuesto.ejecucion)")
        return
    m = pd.read_csv(ruta)

    fig, ax = plt.subplots(figsize=(9, 5.6))
    colores = {2024: AZUL, 2025: ROJO, 2026: GRIS}
    for anio, g in m.groupby("anio"):
        g = g.sort_values("mes")
        vig = g["ValorVigente"].iloc[-1]
        ax.plot(g["mes"], 100 * g["ValorCompromiso"] / vig, color=colores.get(anio, GRIS),
                lw=2, ls="--", alpha=0.75)
        ax.plot(g["mes"], 100 * g["ValorGiros"] / vig, color=colores.get(anio, GRIS),
                lw=2.6, marker="o", ms=4, label=str(anio))

    ax.plot([1, 12], [8.33, 100], color=TINTA, lw=1, ls=":", zorder=0)
    ax.text(9.2, 88, "ritmo lineal\n(1/12 por mes)", fontsize=8, color=TINTA, ha="left")

    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    ax.set_xlabel("Mes")
    ax.set_ylabel("% del presupuesto vigente")
    ax.set_ylim(0, 105)
    ax.set_title(
        "IDRD — el dinero se compromete temprano y se paga tarde\n"
        "Línea gruesa: girado (pagado). Línea punteada: comprometido (contratado)",
        loc="left",
    )
    ax.legend(loc="upper left", title="Vigencia")
    pie_de_fuente(
        fig,
        "Fuente: Presupuesto General del Distrito — Secretaría Distrital de Hacienda, "
        "cortes mensuales 2024-01 a 2026-05. 2026 va hasta mayo.",
    )
    guardar(fig, "04_curva_ejecucion_idrd")


# --------------------------------------------------------------------------
# Figura 5 — Cuándo arrancan los contratos
# --------------------------------------------------------------------------
def fig_calendario_contratacion() -> None:
    ruta = PROC / "contratos_calendario_tipo.csv"
    if not ruta.exists():
        print("  (falta contratos_calendario_tipo.csv — corré python -m notebooks.presupuesto.contratos)")
        return
    d = pd.read_csv(ruta)
    meses = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    anios = [a for a in (2024, 2025) if a in set(d["anio"])]

    fig, axes = plt.subplots(1, len(anios), figsize=(10.5, 4.6), sharey=True)

    for ax, anio in zip(axes, anios):
        g = d[d["anio"] == anio]
        etq_log = "Viajes, comida, uniformes y eventos"
        log = g[g["tipo_objeto"] == etq_log].set_index("mes")["valor_mm"]
        res = g[g["tipo_objeto"] == "Todo lo demás"].set_index("mes")["valor_mm"]
        log = log.reindex(range(1, 13)).fillna(0)
        res = res.reindex(range(1, 13)).fillna(0)

        ax.bar(range(1, 13), res, color=AZUL_CLARO, width=0.74, label="Todo lo demás")
        ax.bar(range(1, 13), log, bottom=res, color=ROJO, width=0.74, label=etq_log)
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(meses)
        ax.set_title(str(anio), loc="left", fontsize=11)

    axes[0].set_ylabel("Plata contratada (millones de pesos)")
    axes[0].legend(loc="upper left", fontsize=9)
    fig.suptitle(
        "Los programas de actividad física se contratan al final del año",
        x=0.007, y=1.03, ha="left", va="top", fontsize=13, fontweight="bold",
    )
    guardar(fig, "05_calendario_contratacion")


# --------------------------------------------------------------------------
# Figura 6 — Ejecución de los Fondos de Desarrollo Local
# --------------------------------------------------------------------------
def fig_ejecucion_fdl() -> None:
    ruta = PROC / "ejecucion_fdl_anual.csv"
    if not ruta.exists():
        print("  (falta ejecucion_fdl_anual.csv — corré python -m notebooks.presupuesto.ejecucion)")
        return
    d = pd.read_csv(ruta)
    d = d[d["anio"] == 2025].sort_values("pct_girado")
    y = range(len(d))

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(list(y), d["pct_comprometido"], color=GRIS_TENUE, height=0.74,
            label="Comprometido (contratado)")
    ax.barh(list(y), d["pct_girado"], color=ROJO, height=0.46,
            label="Girado (pagado)")

    for i, (_, r) in enumerate(d.iterrows()):
        ax.text(r["pct_girado"] + 1.2, i, f"{r['pct_girado']:.0f}%", va="center",
                fontsize=8, color=TINTA)

    ax.set_yticks(list(y))
    ax.set_yticklabels(d["localidad"])
    ax.set_xlabel("% del presupuesto vigente, cierre de 2025")
    ax.set_xlim(0, 108)
    ax.set_title(
        "El rezago del pago es de todo el Distrito, no solo del deporte\n"
        "Los 20 Fondos de Desarrollo Local contratan casi todo su presupuesto\n"
        "y ninguno alcanza a pagar ni el 70%",
        loc="left",
    )
    ax.legend(loc="lower right", fontsize=9)
    pie_de_fuente(
        fig,
        "Presupuesto General del Distrito — Secretaría Distrital de Hacienda. "
        "Inversión de los Fondos de Desarrollo Local, vigencia 2025 cerrada.\n"
        "IMPORTANTE: es la inversión local de TODOS los sectores (vías, seguridad, "
        "cultura, deporte). En esta fuente los FDL no traen desagregación sectorial, "
        "así que no es el presupuesto de actividad física.",
    )
    guardar(fig, "06_ejecucion_fdl")


# --------------------------------------------------------------------------
# Figura 7 — Cuadrantes riesgo × inversión per cápita
# --------------------------------------------------------------------------
OUTLIERS_TAMANO = ("Sumapaz", "La Candelaria")


def fig_cuadrantes() -> None:
    ruta = PROC / "cruce_final.csv"
    if not ruta.exists():
        print("  (falta cruce_final.csv — corré python -m notebooks.presupuesto.cruce)")
        return
    d = pd.read_csv(ruta)
    d = d[~d["localidad"].isin(OUTLIERS_TAMANO)].copy()

    fig, ax = plt.subplots(figsize=(9, 7))
    mx, my = d["af_pc"].median(), d["indice_riesgo"].median()
    ax.axvline(mx, color=GRIS, ls="--", lw=1)
    ax.axhline(my, color=GRIS, ls="--", lw=1)

    ax.fill_between([d["af_pc"].min() * 0.9, mx], my, 100, color=ROJO, alpha=0.06, zorder=0)
    ax.text(d["af_pc"].min() * 0.95, 97, "Riesgo alto,\ninversión baja",
            fontsize=9, color=ROJO, weight="bold", va="top")

    sc = ax.scatter(
        d["af_pc"], d["indice_riesgo"], s=210, c=d["pct_girado"],
        cmap="RdYlGn", vmin=44, vmax=70, edgecolor=TINTA, linewidth=0.8, zorder=3,
    )
    cb = fig.colorbar(sc, ax=ax, pad=0.02)
    cb.set_label("% del presupuesto girado (FDL, cierre 2025)", fontsize=9)
    cb.outline.set_visible(False)

    etiquetas = [
        ax.text(r["af_pc"], r["indice_riesgo"], r["localidad"], fontsize=8.2, color=TINTA)
        for _, r in d.iterrows()
    ]
    try:
        from adjustText import adjust_text

        adjust_text(etiquetas, ax=ax, expand=(1.15, 1.35),
                    arrowprops=dict(arrowstyle="-", color=GRIS, lw=0.6))
    except ImportError:
        pass

    ax.set_xlabel("Plata por habitante para actividad física (pesos, 2025-2028)")
    ax.set_ylabel("Índice de riesgo por inactividad física")
    ax.set_title(
        "La plata sí va donde está el riesgo — pero llega más lento\n"
        "Entre más arriba, más riesgo. Entre más a la derecha, más plata.\n"
        "El color muestra cuánto de esa plata se alcanzó a pagar",
        loc="left",
    )
    pie_de_fuente(
        fig,
        "Elaboración propia. Inversión: proyectos de desarrollo local, sector deporte y "
        "recreación (SDP). Población: proyecciones SDP-DANE 2025. Riesgo: SDS-OSB. "
        "Excluye Sumapaz y La Candelaria (poblaciones atípicamente pequeñas).",
    )
    guardar(fig, "07_cuadrantes_riesgo_inversion")


# --------------------------------------------------------------------------
# Figura 8 — La plata y el servicio van por caminos distintos
# --------------------------------------------------------------------------
def fig_plata_vs_servicio() -> None:
    ruta = PROC / "cruce_final.csv"
    if not ruta.exists():
        print("  (falta cruce_final.csv — corré python -m notebooks.presupuesto.cruce)")
        return
    d = pd.read_csv(ruta)
    if "sesiones_pc_100k" not in d.columns:
        print("  (falta la capa de oferta — corré python -m notebooks.presupuesto.oferta)")
        return
    d = d[~d["localidad"].isin(OUTLIERS_TAMANO)].copy()

    fig, ax = plt.subplots(figsize=(9.5, 6.8))
    sin = d["sesiones"] == 0

    ax.axhspan(-0.35, 0.35, color=ROJO, alpha=0.07, zorder=0)
    ax.text(d["af_pc"].max() * 0.99, 0.55, "sin ninguna sesión",
            ha="right", fontsize=9.5, color=ROJO, weight="bold")

    sc = ax.scatter(
        d["af_pc"], d["sesiones_pc_100k"], s=230,
        c=d["indice_riesgo"], cmap="RdYlBu_r", vmin=10, vmax=95,
        edgecolor=TINTA, linewidth=0.9, zorder=3,
    )
    cb = fig.colorbar(sc, ax=ax, pad=0.02)
    cb.set_label("Índice de riesgo por inactividad física", fontsize=9)
    cb.outline.set_visible(False)

    etiquetas = []
    for _, r in d.iterrows():
        peso = "bold" if (r["sesiones"] == 0 and r["rank_riesgo"] <= 7) else "normal"
        etiquetas.append(
            ax.text(r["af_pc"], r["sesiones_pc_100k"], r["localidad"],
                    fontsize=8.4, color=TINTA, fontweight=peso)
        )
    try:
        from adjustText import adjust_text

        adjust_text(etiquetas, ax=ax, expand=(1.15, 1.4),
                    arrowprops=dict(arrowstyle="-", color=GRIS, lw=0.6))
    except ImportError:
        pass

    ax.set_xlabel("Plata por habitante para actividad física (pesos, 2025-2028)")
    ax.set_ylabel("Clases por semana por cada 100.000 personas de 15 años o más")
    ax.set_title(
        "La plata y el servicio van por caminos distintos\n"
        "Las de la franja roja reciben presupuesto y no tienen ninguna clase",
        loc="left",
    )
    ax.set_ylim(-1.2, None)
    pie_de_fuente(
        fig,
        "Inversión: proyectos de desarrollo local, sector deporte y recreación (SDP). "
        "Oferta: Escuelas Deportivas Adultos del IDRD, programación publicada en idrd.gov.co "
        "(187 sesiones semanales, agosto 2026). Población: SDP-DANE 2025. "
        "Excluye Sumapaz y La Candelaria.",
    )
    guardar(fig, "08_plata_vs_servicio")


# --------------------------------------------------------------------------
# Figura 9 — Mapa de calor: oferta por localidad y disciplina
# --------------------------------------------------------------------------
def fig_oferta_disciplina() -> None:
    ruta = ROOT / "data" / "interim" / "idrd_escuelas_adultos.csv"
    cruce = PROC / "cruce_final.csv"
    if not ruta.exists() or not cruce.exists():
        return
    import numpy as np

    from .localidades import normalizar

    df = pd.read_csv(ruta, sep=";")
    df["localidad"] = normalizar(df["localidad"])["localidad"]
    orden = pd.read_csv(cruce).sort_values("rank_riesgo")["localidad"].tolist()

    piv = (
        df.pivot_table(index="localidad", columns="disciplina",
                       values="sesiones_semana", aggfunc="sum")
        .reindex(orden).fillna(0)
    )
    piv = piv[["Atletismo", "Boxeo", "Fútbol Sala", "Padel", "Tenis de Campo"]]

    fig, ax = plt.subplots(figsize=(8.2, 8))
    im = ax.imshow(piv.values, cmap="YlOrRd", aspect="auto", vmin=0, vmax=30)
    ax.set_xticks(range(len(piv.columns)))
    ax.set_xticklabels(piv.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(piv)))
    ax.set_yticklabels([f"{i+1}. {n}" for i, n in enumerate(piv.index)])
    ax.set_ylabel("Localidades ordenadas por riesgo (1 = mayor)")

    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = int(piv.values[i, j])
            ax.text(j, i, v if v else "·", ha="center", va="center",
                    fontsize=8.5, color="white" if v > 16 else TINTA)

    ax.set_xticks(np.arange(-.5, piv.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-.5, piv.shape[0], 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)

    fig.colorbar(im, ax=ax, pad=0.02, label="Sesiones semanales")
    ax.set_title(
        "Escuelas Deportivas Adultos: qué hay y dónde\n"
        "Las cuatro filas de arriba son las de mayor riesgo de la ciudad",
        loc="left",
    )
    pie_de_fuente(
        fig,
        "Fuente: programación publicada en idrd.gov.co (agosto 2026). "
        "Tenis y padel exigen implemento propio y son el 42% de la oferta total.",
    )
    guardar(fig, "09_oferta_por_disciplina")


# --------------------------------------------------------------------------
# Figura 10 — Curvas de concentración: ¿el esfuerzo está donde toca?
# --------------------------------------------------------------------------
def fig_curvas_concentracion() -> None:
    ruta = PROC / "cruce_final.csv"
    if not ruta.exists():
        return
    import numpy as np

    from .equidad import DIMENSIONES, indice_concentracion

    d = pd.read_csv(ruta)
    if "sesiones" not in d.columns:
        print("  (falta la capa de oferta — corré python -m notebooks.presupuesto.oferta y src.cruce)")
        return

    pob = d["poblacion_total"].to_numpy()
    nec = d["indice_riesgo"].to_numpy()

    colores = [AZUL, AZUL_CLARO, GRIS, ROJO_CLARO, ROJO]
    estilos = ["-", "-", "--", "-", "-"]

    fig, ax = plt.subplots(figsize=(8.6, 7.4))
    ax.plot([0, 1], [0, 1], color=TINTA, lw=1.2, ls=":", zorder=1)
    ax.text(0.52, 0.47, "reparto proporcional\na la población", fontsize=8.5,
            color=TINTA, rotation=38, ha="left", va="top")

    for (col, etiqueta, _), color, ls in zip(DIMENSIONES, colores, estilos):
        if col not in d.columns:
            continue
        esf = pd.to_numeric(d[col], errors="coerce").fillna(0).to_numpy()
        if esf.sum() == 0:
            continue
        ic, x, y = indice_concentracion(esf, pob, nec)
        # En vez del índice técnico, la cifra directamente legible: qué parte
        # del esfuerzo recibe la mitad de la ciudad que peor está.
        orden = np.argsort(-nec)
        acum = (pob[orden] / pob.sum()).cumsum()
        corte = np.searchsorted(acum, 0.5) + 1
        share = 100 * esf[orden][:corte].sum() / esf.sum()
        ax.plot(x, y, color=color, lw=2.4, ls=ls, zorder=3,
                label=f"{etiqueta} — {share:.0f}%")

    ax.fill_between([0, 1], [0, 1], [1, 1], color=AZUL, alpha=0.05, zorder=0)
    ax.fill_between([0, 1], [0, 0], [0, 1], color=ROJO, alpha=0.05, zorder=0)
    ax.text(0.03, 0.95, "por encima:\nva donde toca", fontsize=9, color=AZUL,
            weight="bold", va="top")
    ax.text(0.97, 0.06, "por debajo:\nva al revés", fontsize=9, color=ROJO,
            weight="bold", ha="right", va="bottom")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Habitantes de Bogotá, empezando por los de mayor riesgo →")
    ax.set_ylabel("Parte del esfuerzo que reciben")
    ax.set_title(
        "El esfuerzo se degrada en cada paso\n"
        "El porcentaje es lo que recibe la mitad de la ciudad que peor está.\n"
        "Si el reparto fuera parejo, sería 50%",
        loc="left",
    )
    ax.legend(loc="upper left", bbox_to_anchor=(0.015, 0.83), fontsize=8.4)
    pie_de_fuente(
        fig,
        "Cálculo propio, ponderado por población, con las 20 localidades. "
        "Riesgo: Secretaría Distrital de Salud. Presupuesto: proyectos de desarrollo local "
        "(Secretaría Distrital de Planeación). Clases: idrd.gov.co, agosto 2026.",
    )
    guardar(fig, "10_curvas_concentracion")


# --------------------------------------------------------------------------
# Figura 11 — El veredicto depende de la vara con que se mida
# --------------------------------------------------------------------------
def fig_matriz_equidad() -> None:
    ruta = ROOT / "outputs" / "tables" / "matriz_equidad.csv"
    if not ruta.exists():
        print("  (falta matriz_equidad.csv — corré python -m notebooks.presupuesto.equidad)")
        return
    import numpy as np

    m = pd.read_csv(ruta).set_index("esfuerzo")
    # Filas de arriba: la plata. Filas de abajo: el servicio.
    orden = [i for i in [
        "Presupuesto programado (PDL)",
        "Presupuesto efectivamente girado",
        "Inversión en parques de proximidad",
        "Sesiones semanales de escuelas deportivas",
        "Escenarios con oferta",
    ] if i in m.index]
    m = m.loc[orden]
    etiquetas_fila = [
        "Plata programada",
        "Plata efectivamente pagada",
        "Plata en parques de barrio",
        "Clases de escuelas deportivas",
        "Parques con clases",
    ][: len(m)]

    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    vmax = float(np.abs(m.values).max())
    im = ax.imshow(m.values, cmap="RdBu", vmin=-vmax, vmax=vmax, aspect="auto")

    ax.set_xticks(range(m.shape[1]))
    ax.set_xticklabels([c.replace(" (", "\n(") for c in m.columns], fontsize=9.2)
    ax.set_yticks(range(m.shape[0]))
    ax.set_yticklabels(etiquetas_fila, fontsize=9.6)

    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.values[i, j]
            señal = "va donde toca" if v > 0.05 else "va al revés" if v < -0.05 else "parejo"
            ax.text(j, i - 0.13, f"{v:+.2f}".replace(".", ","), ha="center", va="center",
                    fontsize=13, fontweight="bold",
                    color="white" if abs(v) > vmax * 0.55 else TINTA)
            ax.text(j, i + 0.22, señal, ha="center", va="center", fontsize=8.2,
                    color="white" if abs(v) > vmax * 0.55 else GRIS)

    ax.set_xticks(np.arange(-.5, m.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-.5, m.shape[0], 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2.2)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    ax.tick_params(axis="x", length=0)
    ax.xaxis.set_ticks_position("top")

    ax.set_title(
        "El veredicto cambia según a quién definamos como el que más lo necesita\n"
        "Azul: el esfuerzo llega a los que más lo necesitan.  Rojo: llega a los que menos.",
        loc="left", pad=42,
    )
    pie_de_fuente(
        fig,
        "Cálculo propio ponderado por población, las 20 localidades. Cada columna reordena "
        "la ciudad con un criterio distinto de necesidad y vuelve a medir el mismo reparto.\n"
        "Ojo: en Bogotá las localidades con más población de 45+ son también las de mayor "
        "ingreso, así que esa columna no separa edad de riqueza.",
    )
    guardar(fig, "11_matriz_equidad")


# --------------------------------------------------------------------------
# Figura 12 — ¿Se entrega lo prometido?
# --------------------------------------------------------------------------
def fig_avance_fisico() -> None:
    ruta = PROC / "desempeno_actividades_af.csv"
    if not ruta.exists():
        print("  (falta desempeno_actividades_af.csv — corré python -m notebooks.presupuesto.desempeno)")
        return
    from .desempeno import AVANCE_TIEMPO

    d = pd.read_csv(ruta).sort_values("avance_fis")
    y = range(len(d))

    fig, ax = plt.subplots(figsize=(10.4, 6.6))
    ax.axvline(AVANCE_TIEMPO, color=TINTA, ls="--", lw=1.3, zorder=1)
    ax.text(AVANCE_TIEMPO + 0.8, len(d) - 0.3,
            f"debería ir en {AVANCE_TIEMPO:.0f}%\n(tiempo transcurrido)",
            fontsize=9, color=TINTA, va="top")

    ax.barh(list(y), d["avance_fis"], height=0.62, zorder=3,
            color=[GRIS_TENUE if v == 0 else ROJO if v < 20 else ROJO_CLARO
                   for v in d["avance_fis"]],
            label="Lo que dicen que entregaron")
    ax.scatter(d["avance_fin"], list(y), s=34, color=AZUL, zorder=4,
               label="Lo que pagaron")

    for i, v in enumerate(d["avance_fis"]):
        ax.text(v + 0.7, i, "0%" if v == 0 else f"{v:.0f}%", va="center",
                fontsize=8.4, color=TINTA)

    ax.set_yticks(list(y))
    ax.set_yticklabels(d["actividad"], fontsize=8.4)
    ax.set_xlabel("% de la meta del cuatrienio")
    ax.set_xlim(0, 50)
    ax.set_title(
        "Ninguna meta va al ritmo que debería\n"
        "Los dos proyectos de actividad física del IDRD, a septiembre de 2025",
        loc="left",
    )
    ax.legend(loc="lower right", fontsize=9)
    pie_de_fuente(
        fig,
        "Proyectos de Inversión (Secretaría Distrital de Planeación), proyectos 8154 y 8155. "
        "Las magnitudes las reporta la propia entidad y no hay verificación independiente.",
    )
    guardar(fig, "12_avance_fisico")


# --------------------------------------------------------------------------
# Figura 13 — Lo que el catálogo promete vs lo que existe
# --------------------------------------------------------------------------
def fig_promesa_vs_realidad() -> None:
    ruta = ROOT / "outputs" / "tables" / "brecha_catalogo_60mas.csv"
    if not ruta.exists():
        print("  (falta brecha_catalogo_60mas.csv — corré python -m notebooks.presupuesto.scrape_60mas)")
        return
    b = pd.read_csv(ruta)
    riesgo = pd.read_csv(PROC / "cruce_final.csv")[
        ["cod_localidad", "rank_riesgo", "poblacion_60_mas"]
    ]
    d = b.merge(riesgo, on="cod_localidad").sort_values("rank_riesgo", ascending=False)
    y = range(len(d))
    vacia = d["sesiones"] == 0

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 7.6), sharey=True)

    a1.barh(list(y), d["programas_declarados"], height=0.68,
            color=[ROJO if v else GRIS_TENUE for v in vacia])
    a1.set_xlim(0, 16)
    a1.set_xlabel("Programas que el catálogo dice que hay")
    a1.set_title("Lo que promete el IDRD", loc="left", fontsize=11.5)
    for i, v in enumerate(d["programas_declarados"]):
        a1.text(v - 0.5, i, str(int(v)), va="center", ha="right",
                fontsize=8.4, color="white", fontweight="bold")

    a2.barh(list(y), d["sesiones"], height=0.68,
            color=[ROJO if v else AZUL_CLARO for v in vacia])
    a2.set_xlabel("Clases por semana que realmente existen")
    a2.set_title("Lo que un ciudadano encuentra", loc="left", fontsize=11.5)
    for i, v in enumerate(d["sesiones"]):
        a2.text(v + 1, i, "ninguna" if v == 0 else str(int(v)), va="center",
                fontsize=8.4, color=ROJO if v == 0 else TINTA,
                fontweight="bold" if v == 0 else "normal")
    a2.set_xlim(0, 70)

    a1.set_yticks(list(y))
    a1.set_yticklabels(
        [f"{r.localidad}  ·  #{int(r.rank_riesgo)}" for r in d.itertuples()],
        fontsize=9,
    )
    a1.set_ylabel("Localidades ordenadas por riesgo (#1 = mayor riesgo)")

    n = int(vacia.sum())
    fig.suptitle(
        "El catálogo promete lo mismo en las 20 localidades.\n"
        f"En {n} de ellas no hay ni una sola clase.",
        x=0.007, y=1.05, ha="left", va="top", fontsize=13.5, fontweight="bold",
    )
    pie_de_fuente(
        fig,
        "Izquierda: catálogo idrd.gov.co filtrado a mayores de 60, una consulta por localidad. "
        "Derecha: programación publicada de Escuelas Deportivas Adultos, el único de esos 14 "
        "programas con horarios verificables.\nEn rojo, las 8 localidades donde el programa "
        "figura como disponible y no tiene sesiones: 1.908.497 personas, el 24% de Bogotá.",
    )
    guardar(fig, "13_promesa_vs_realidad")


def main() -> int:
    aplicar_estilo()
    print("Generando figuras de ejecución...")
    fig_promesa_vs_realidad()
    fig_avance_fisico()
    fig_matriz_equidad()
    fig_curvas_concentracion()
    fig_cuadrantes()
    fig_plata_vs_servicio()
    fig_oferta_disciplina()
    fig_curva_ejecucion_idrd()
    fig_calendario_contratacion()
    fig_ejecucion_fdl()

    ruta = PROC / "riesgo_localidad.csv"
    if not ruta.exists():
        print("Falta data/processed/presupuesto/riesgo_localidad.csv — corré: python -m notebooks.presupuesto.riesgo")
        return 1
    riesgo = pd.read_csv(ruta)
    print("Generando figuras de riesgo...")
    fig_dumbbell_inactividad(riesgo)
    fig_indice_riesgo(riesgo)
    fig_dispersion_riesgo(riesgo)
    print("Listo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
