"""
Normalización de localidades de Bogotá.

Este módulo es el contrato entre las tres personas del equipo: TODO join
territorial pasa por `normalizar()`. Los datasets distritales escriben el
nombre de la localidad de seis maneras distintas (con/sin tilde, mayúsculas,
"RAFAEL URIBE" vs "RAFAEL URIBE URIBE", códigos DANE de 2 dígitos, etc.).
Si cada uno normaliza a su manera, los merges pierden filas en silencio.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

# Código oficial de localidad (Decreto 1421/93) -> nombre canónico
CODIGO_A_NOMBRE = {
    1: "Usaquén",
    2: "Chapinero",
    3: "Santa Fe",
    4: "San Cristóbal",
    5: "Usme",
    6: "Tunjuelito",
    7: "Bosa",
    8: "Kennedy",
    9: "Fontibón",
    10: "Engativá",
    11: "Suba",
    12: "Barrios Unidos",
    13: "Teusaquillo",
    14: "Los Mártires",
    15: "Antonio Nariño",
    16: "Puente Aranda",
    17: "La Candelaria",
    18: "Rafael Uribe Uribe",
    19: "Ciudad Bolívar",
    20: "Sumapaz",
}

NOMBRE_A_CODIGO = {v: k for k, v in CODIGO_A_NOMBRE.items()}

# Etiquetas que NO son una localidad y deben excluirse de los per cápita
AGREGADOS = {
    "bogota dc",
    "bogota d c",
    "bogota",
    "total",
    "total bogota",
    "distrito",
    "distrito capital",
    "no aplica",
    "sin localidad",
    "todas las localidades",
    "ciudad",
}


def _slug(texto: str) -> str:
    """minúsculas, sin tildes, sin puntuación, espacios colapsados."""
    if texto is None:
        return ""
    s = str(texto).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Alias observados en los datasets distritales -> código de localidad
_ALIAS = {
    "usaquen": 1,
    "chapinero": 2,
    "santa fe": 3, "santafe": 3, "santa fe de bogota": 3,
    "san cristobal": 4, "san cristobal sur": 4,
    "usme": 5,
    "tunjuelito": 6,
    "bosa": 7,
    "kennedy": 8,
    "fontibon": 9,
    "engativa": 10,
    "suba": 11,
    "barrios unidos": 12,
    "teusaquillo": 13,
    "los martires": 14, "martires": 14,
    "antonio narino": 15,
    "puente aranda": 16,
    "la candelaria": 17, "candelaria": 17,
    "rafael uribe uribe": 18, "rafael uribe": 18,
    "ciudad bolivar": 19,
    "sumapaz": 20,
}


def a_codigo(valor) -> float | None:
    """Devuelve el código 1-20 de localidad, o None si es agregado/desconocido.

    Acepta nombre en cualquier grafía, o un código numérico ('05', 5, '5.0').
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None

    # ¿Es un código numérico?
    txt = str(valor).strip()
    if re.fullmatch(r"\d{1,2}(\.0+)?", txt):
        cod = int(float(txt))
        return cod if cod in CODIGO_A_NOMBRE else None

    s = _slug(txt)
    if s in AGREGADOS:
        return None
    if s in _ALIAS:
        return _ALIAS[s]

    # Búsqueda laxa: el nombre canónico aparece contenido en el texto
    # (cubre casos tipo "LOCALIDAD 04 - SAN CRISTOBAL")
    for alias, cod in _ALIAS.items():
        if re.search(rf"\b{re.escape(alias)}\b", s):
            return cod
    return None


def normalizar(serie: pd.Series) -> pd.DataFrame:
    """Serie de localidades (texto o código) -> DataFrame [cod_localidad, localidad].

    Las filas que no mapean quedan con NaN; nunca se descartan en silencio.
    """
    cod = serie.map(a_codigo)
    return pd.DataFrame(
        {
            "cod_localidad": cod,
            "localidad": cod.map(lambda c: CODIGO_A_NOMBRE.get(c) if pd.notna(c) else None),
        },
        index=serie.index,
    )


def reporte_cobertura(serie: pd.Series, nombre_fuente: str = "") -> pd.DataFrame:
    """Qué valores NO se pudieron mapear y cuántas filas representan.

    Úsenlo siempre después de normalizar. Si un valor no mapeado tiene mucho
    peso (p.ej. 'DISTRITAL' con el 60% del presupuesto), eso no es un bug de
    limpieza: es un hallazgo sobre la territorialización del gasto.
    """
    tmp = pd.DataFrame({"original": serie, "cod": serie.map(a_codigo)})
    fallidos = (
        tmp[tmp["cod"].isna()]
        .groupby("original", dropna=False)
        .size()
        .sort_values(ascending=False)
        .rename("filas")
        .reset_index()
    )
    fallidos.insert(0, "fuente", nombre_fuente)
    return fallidos
