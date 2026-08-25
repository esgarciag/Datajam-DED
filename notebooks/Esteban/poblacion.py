"""
Población por localidad, edad y sexo — proyecciones SDP/DANE 2005-2035.

El archivo viene en .ods, con 4 filas en blanco arriba, encabezado en la fila
5 y formato ancho: una columna por combinación sexo × edad simple
(`Hombres_0` ... `Mujeres_100`). Acá se pasa a formato largo y se agregan los
grupos etarios que necesita el análisis.

Grupos:
  total     toda la población, denominador de los per cápita generales
  15_mas    población en edad de hacer actividad física de forma autónoma
  45_mas    ventana donde se materializa el riesgo cardiometabólico; es el
            denominador correcto para el modelo de costos en salud
  60_mas    persona mayor; corresponde al público de Pasaporte Vital

    python -m src.poblacion
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .localidades import CODIGO_A_NOMBRE

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"

PATRON = "*localidad_proyeccion_retroproyeccion_poblacion*"
FILA_ENCABEZADO = 4


def _ruta() -> Path:
    for ext in ("ods", "xlsx", "xls"):
        hits = sorted(RAW.glob(f"{PATRON}.{ext}"))
        if hits:
            return hits[0]
    raise FileNotFoundError(
        f"No encuentro el archivo de población en {RAW}. "
        "Debe coincidir con el patrón *localidad_proyeccion_retroproyeccion_poblacion*"
    )


def cargar_largo() -> pd.DataFrame:
    ruta = _ruta()
    motor = "odf" if ruta.suffix == ".ods" else None
    df = pd.read_excel(ruta, engine=motor, header=FILA_ENCABEZADO)
    df.columns = [str(c).strip() for c in df.columns]
    print(f"[poblacion] fuente: {ruta.name} ({df.shape[0]} filas × {df.shape[1]} col)")

    meta = ["Código Localidad", "Nombre Localidad", "Área", "AÑO"]
    faltan = [c for c in meta if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas esperadas: {faltan}. Vi: {list(df.columns)[:12]}")

    cols_edad = [c for c in df.columns if re.fullmatch(r"(Hombres|Mujeres)_\d+", c)]
    print(f"[poblacion] columnas sexo×edad detectadas: {len(cols_edad)}")

    largo = df.melt(id_vars=meta, value_vars=cols_edad,
                    var_name="sexo_edad", value_name="personas")
    partes = largo["sexo_edad"].str.split("_", expand=True)
    largo["sexo"] = partes[0]
    largo["edad"] = pd.to_numeric(partes[1], errors="coerce")
    largo["personas"] = pd.to_numeric(largo["personas"], errors="coerce").fillna(0)
    largo["cod_localidad"] = pd.to_numeric(largo["Código Localidad"], errors="coerce")
    largo["anio"] = pd.to_numeric(largo["AÑO"], errors="coerce")

    largo = largo[largo["cod_localidad"].between(1, 20)]
    largo["localidad"] = largo["cod_localidad"].map(CODIGO_A_NOMBRE)
    return largo.drop(columns=["sexo_edad", "Código Localidad", "Nombre Localidad"])


def grupos_por_localidad(largo: pd.DataFrame, anio: int) -> pd.DataFrame:
    """Una fila por localidad con los denominadores del análisis."""
    d = largo[largo["anio"] == anio]
    if d.empty:
        raise ValueError(f"No hay datos para {anio}. Años: {sorted(largo['anio'].unique())[:5]}...")

    def suma(cond=None) -> pd.Series:
        sub = d if cond is None else d[cond]
        return sub.groupby(["cod_localidad", "localidad"])["personas"].sum()

    out = pd.DataFrame({
        "poblacion_total": suma(),
        "poblacion_15_mas": suma(d["edad"] >= 15),
        "poblacion_45_mas": suma(d["edad"] >= 45),
        "poblacion_60_mas": suma(d["edad"] >= 60),
    }).reset_index()
    out["pct_45_mas"] = 100 * out["poblacion_45_mas"] / out["poblacion_total"]
    out["pct_60_mas"] = 100 * out["poblacion_60_mas"] / out["poblacion_total"]
    out["anio"] = anio
    return out.sort_values("poblacion_total", ascending=False).reset_index(drop=True)


def main() -> int:
    PROC.mkdir(parents=True, exist_ok=True)
    largo = cargar_largo()
    print(f"[poblacion] años disponibles: {int(largo['anio'].min())}-{int(largo['anio'].max())}")

    anio = 2025
    pob = grupos_por_localidad(largo, anio)
    pob.to_csv(PROC / f"poblacion_localidad_{anio}.csv", index=False, encoding="utf-8")

    total = pob["poblacion_total"].sum()
    print(f"\n--- Población {anio} por localidad ---")
    print(pob[["localidad", "poblacion_total", "poblacion_45_mas",
               "pct_45_mas", "pct_60_mas"]].round(1).to_string(index=False))
    print(f"\nTotal Bogotá {anio}: {total:,.0f}")

    assert len(pob) == 20, f"Se esperaban 20 localidades, hay {len(pob)}"
    assert 7.5e6 < total < 9e6, f"Total Bogotá fuera de rango plausible: {total:,.0f}"

    # Serie para el modelo de costos: 45+ proyectada a futuro
    fut = pd.concat([grupos_por_localidad(largo, a) for a in (2025, 2030, 2035)])
    fut.to_csv(PROC / "poblacion_localidad_proyeccion.csv", index=False, encoding="utf-8")
    print("\n--- Crecimiento de la población 45+ (Bogotá) ---")
    print(fut.groupby("anio")[["poblacion_total", "poblacion_45_mas", "poblacion_60_mas"]]
          .sum().astype(int).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
