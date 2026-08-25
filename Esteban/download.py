"""
Descarga de todas las fuentes a data/raw/.

Ejecutar desde la raíz del proyecto:
    python -m src.download

Nota: los CSV de Mapa de Inversiones son grandes (Contratos puede pesar
cientos de MB). Se descargan en streaming y se cachean: si el archivo ya
existe no se vuelve a bajar salvo que se pase --force.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

BLOB = "https://adlsinversionesbogota.blob.core.windows.net/opendata"

FUENTES: dict[str, str] = {
    # --- Mapa de Inversiones Bogotá (SDH / SDP / Secretaría General) ---
    "presupuesto_general.csv": f"{BLOB}/DatosAbiertosPresupuestoGeneralDistrito.csv",
    "proyectos_inversion.csv": f"{BLOB}/DatosAbiertosProyectosInversion.csv",
    "proyectos_desarrollo_local.csv": f"{BLOB}/DatosAbiertosProyectosDesarrolloLocal.csv",
    "proyectos_pot.csv": f"{BLOB}/DatosAbiertosProyectosPOT.csv",
    "proyectos_pot_localizacion.csv": f"{BLOB}/DatosAbiertosProyectosPOTLocalizacion.csv",
    "contratos.csv": f"{BLOB}/DatosAbiertosContratos.csv",
    # --- Diccionarios (para saber qué significa cada columna) ---
    "dicc_presupuesto_general.xlsx": f"{BLOB}/DatosAbiertosPresupuestoGeneralDistrito_Diccionario.xlsx",
    "dicc_proyectos_inversion.xlsx": f"{BLOB}/DatosAbiertosProyectosInversion_Diccionario.xlsx",
    "dicc_proyectos_desarrollo_local.xlsx": f"{BLOB}/DatosAbiertosProyectosDesarrolloLocal_Diccionario.xlsx",
    "dicc_contratos.xlsx": f"{BLOB}/DatosAbiertosContratosDistrito_Diccionario.xlsx",
    # --- SDP: proyecciones de población por localidad (denominador) ---
    # Formato .ods; requiere odfpy para leerlo con pandas.
    "sdp_poblacion_localidad.ods": (
        "https://datosabiertos.bogota.gov.co/dataset/0f1fb76a-1595-43d5-9257-0abcc3db908a/"
        "resource/5669484f-dc1d-4457-b1d1-de0a3825b41c/download/"
        "202503_localidad_proyeccion_retroproyeccion_poblacion_2005_2035.ods"
    ),
    # --- Secretaría Distrital de Salud: actividad física por localidad ---
    "sds_actividad_fisica.csv": (
        "https://datosabiertos.bogota.gov.co/dataset/16025ea1-81cc-4947-b684-7a65303bb76b/"
        "resource/f5612407-9407-446c-b504-7ed1d21084ef/download/"
        "osb_enfermedadescronicas-actividadfisica.csv"
    ),
    # --- IDRD: beneficiarios Pasaporte Vital (microdato, I sem 2025) ---
    "idrd_pasaporte_vital.csv": (
        "https://datosabiertos.bogota.gov.co/dataset/a37beaf9-0928-4de8-a76c-8ce73ef1898a/"
        "resource/595c068f-b568-4ada-9c8c-ba3c894d6cbd/download/"
        "beneficiados-pasaporte-vital-idrd_i_semestre_2025.csv"
    ),
    "idrd_pasaporte_vital_diccionario.xlsx": (
        "https://datosabiertos.bogota.gov.co/dataset/a37beaf9-0928-4de8-a76c-8ce73ef1898a/"
        "resource/ba043e18-65c5-4a43-ae3f-9e48e2822482/download/"
        "diccionario_datos_pasaporte_vital.xlsx"
    ),
}


# Nombre tal como lo entrega el navegador -> nombre canónico del proyecto.
# Permite bajar los CSV a mano (clic derecho > Guardar) y soltarlos en
# data/raw/ sin renombrar: normalizar_nombres() los acomoda.
ALIAS_ARCHIVOS = {
    "datosabiertospresupuestogeneraldistrito": "presupuesto_general.csv",
    "datosabiertosproyectosinversion": "proyectos_inversion.csv",
    "datosabiertosproyectosdesarrollolocal": "proyectos_desarrollo_local.csv",
    "datosabiertosproyectospot": "proyectos_pot.csv",
    "datosabiertosproyectospotlocalizacion": "proyectos_pot_localizacion.csv",
    "datosabiertoscontratos": "contratos.csv",
    "osb_enfermedadescronicas-actividadfisica": "sds_actividad_fisica.csv",
    "beneficiados-pasaporte-vital-idrd_i_semestre_2025": "idrd_pasaporte_vital.csv",
}


def normalizar_nombres(carpeta: Path = RAW, verbose: bool = True) -> list[tuple[str, str]]:
    """Renombra los archivos descargados a mano al nombre canónico.

    Tolera sufijos del navegador tipo ' (1)', '(2)', mayúsculas y espacios.
    Devuelve la lista de renombres aplicados.
    """
    import re as _re

    hechos = []
    for path in sorted(carpeta.glob("*")):
        if not path.is_file():
            continue
        tallo = path.stem.lower().strip()
        tallo = _re.sub(r"\s*\(\d+\)$", "", tallo)      # "archivo (1)" -> "archivo"
        tallo = _re.sub(r"[\s_]+$", "", tallo)
        destino_nombre = ALIAS_ARCHIVOS.get(tallo)
        if not destino_nombre or path.name == destino_nombre:
            continue
        destino = carpeta / destino_nombre
        if destino.exists():
            if verbose:
                print(f"  [omitido] {path.name}: ya existe {destino_nombre}")
            continue
        path.rename(destino)
        hechos.append((path.name, destino_nombre))
        if verbose:
            print(f"  [renombrado] {path.name} -> {destino_nombre}")
    return hechos


def descargar(nombre: str, url: str, force: bool = False) -> Path:
    destino = RAW / nombre
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists() and not force:
        mb = destino.stat().st_size / 1e6
        print(f"  [cache] {nombre:42s} {mb:8.1f} MB")
        return destino

    print(f"  [http ] {nombre:42s} ...", end="", flush=True)
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        tmp = destino.with_suffix(destino.suffix + ".part")
        total = 0
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
                total += len(chunk)
        tmp.replace(destino)
    print(f" {total / 1e6:8.1f} MB")
    return destino


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="volver a descargar aunque exista")
    ap.add_argument("--solo", nargs="*", help="descargar solo estos nombres de archivo")
    args = ap.parse_args(argv)

    objetivo = FUENTES
    if args.solo:
        objetivo = {k: v for k, v in FUENTES.items() if k in set(args.solo)}
        if not objetivo:
            print("Nada que descargar; nombres válidos:", *FUENTES, sep="\n  ")
            return 1

    print(f"Descargando a {RAW}")
    fallos = []
    for nombre, url in objetivo.items():
        try:
            descargar(nombre, url, force=args.force)
        except Exception as exc:  # noqa: BLE001
            print(f" FALLÓ -> {exc}")
            fallos.append((nombre, str(exc)))

    if fallos:
        print("\nDescargas fallidas (bajarlas a mano y dejarlas en data/raw/):")
        for nombre, exc in fallos:
            print(f"  - {nombre}: {exc}")
        return 1

    print("\nListo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
