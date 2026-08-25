# Datajam-DED

# Contexto 
Datajam integrantes etc

# Archivos Estructura e instrucciones de  funcionamiento

## Estructura del repositorio

```
Datajam-DED/
├── README.md               Este archivo
├── requirements.txt        Dependencias de Python
├── .gitignore
│
├── data/                   Datos. Nada de código acá.
│   ├── raw/                Fuentes originales, tal como se descargaron
│   │   ├── datos_por_localidad.xlsx
│   │   ├── EncuestaMultiproposito2021ActividadFisica.csv
│   │   ├── mapas/          Geometría de localidad (shapeMap de Power BI)
│   │   └── sisben/         Volcados crudos del scrapper (no se versionan)
│   └── processed/          Todo lo que produce el código
│       ├── presupuesto/    Ejecución, contratación, desempeño, población
│       ├── poblacion_adulta/
│       ├── poblacion_mayor/
│       └── mapas/          Geometría de barrios con la llave de cruce
│
├── notebooks/              Código, en dos paquetes temáticos
│   ├── presupuesto/        Ejecución presupuestal y contratación
│   │   ├── download.py             Descarga las fuentes a data/raw/
│   │   ├── localidades.py          Normalización territorial (no se ejecuta solo)
│   │   ├── poblacion.py            Denominadores por localidad
│   │   ├── ejecucion.py            Ejecución mensual y anual
│   │   ├── contratos.py            Calendario y timing de contratos
│   │   ├── desempeno.py            Avance físico vs. financiero
│   │   ├── viz.py                  Figuras del análisis
│   │   ├── viz_ejecucion.py        Figuras de la página de ejecución
│   │   └── exportar_powerbi.py     Modelo en estrella para Power BI
│   └── poblacion/          Población por barrio, mapas y priorización
│       ├── mapa.py                                 Mapas de calor por barrio
│       ├── priorizacion.py                         Índice de prioridad
│       ├── poblacion_vs_presupuesto_localidad.py
│       ├── poblacion_vs_actividades_localidad.py
│       └── scrappers/
│           ├── adultos/            scrapper_sisben.py · normalizar_csv.py
│           └── adultos_mayores/    scrapper_sisben.py · normalizar_csv.py
│
├── outputs/                Resultados presentables
│   ├── figuras/            PNG + SVG de los análisis
│   ├── figuras_ejecucion/  Las seis figuras de la página de ejecución
│   ├── tablas/             Tablas de apoyo del informe
│   ├── powerbi/            Modelo en estrella listo para cargar
│   └── mapas/              Mapas de calor HTML
│       ├── poblacion_adulta/
│       └── poblacion_mayor/
│
└── docs/
    └── diccionario_datos.md    Qué significa cada columna de data/processed/
```

Regla de oro sobre dónde escribe cada cosa:

| Carpeta | Qué va | Quién escribe ahí |
|---|---|---|
| `data/raw/` | Lo que se bajó de la fuente, sin tocar | `download.py`, los scrappers, descarga manual |
| `data/processed/` | Tablas derivadas, insumo de otros pasos | Los scripts de análisis |
| `outputs/` | Lo que se muestra: figuras, mapas, Power BI | Los scripts de visualización |

Ningún script usa rutas absolutas: todos resuelven la raíz del repositorio a
partir de `__file__`, así que el proyecto se puede clonar y ejecutar desde
cualquier equipo.

## Instrucciones de funcionamiento

Todo se ejecuta **desde la raíz del repositorio**. En Linux y macOS reemplazá
`py -3` por `python3`.

### 1. Instalación

```bash
git clone https://github.com/<usuario>/Datajam-DED.git
cd Datajam-DED

py -3 -m pip install -r requirements.txt

# Solo si vas a correr los scrappers del Sisbén:
py -3 -m playwright install chromium
```

### 2. Bloque de presupuesto — `notebooks/presupuesto/`

Es un paquete de Python: se ejecuta con `python -m`, **no** con
`python archivo.py` (los módulos se importan entre sí).

```bash
py -3 -m notebooks.presupuesto.download          # baja las fuentes a data/raw/
py -3 -m notebooks.presupuesto.poblacion         # denominadores por localidad
py -3 -m notebooks.presupuesto.ejecucion         # ejecución mensual y anual
py -3 -m notebooks.presupuesto.contratos         # calendario y timing de contratos
py -3 -m notebooks.presupuesto.desempeno         # avance físico vs. financiero
py -3 -m notebooks.presupuesto.viz               # -> outputs/figuras/
py -3 -m notebooks.presupuesto.viz_ejecucion     # -> outputs/figuras_ejecucion/
py -3 -m notebooks.presupuesto.exportar_powerbi  # -> outputs/powerbi/
```

`download.py` cachea: si el archivo ya está en `data/raw/` no lo vuelve a
bajar, salvo que le pases `--force`. Los CSV de Mapa de Inversiones son
grandes (Contratos puede pesar cientos de MB) y por eso están en `.gitignore`.

### 3. Bloque de población — `notebooks/poblacion/`

Scripts independientes, con menú interactivo (1 = adulta, 2 = mayor, 3 = ambas).

```bash
# a) Scrapping del visor del Sisbén — abre Chromium y tarda
py -3 notebooks/poblacion/scrappers/adultos/scrapper_sisben.py
py -3 notebooks/poblacion/scrappers/adultos_mayores/scrapper_sisben.py

# b) Normalización de nombres de barrio y construcción de la clave
py -3 notebooks/poblacion/scrappers/adultos/normalizar_csv.py
py -3 notebooks/poblacion/scrappers/adultos_mayores/normalizar_csv.py

# c) Análisis
py -3 notebooks/poblacion/poblacion_vs_presupuesto_localidad.py
py -3 notebooks/poblacion/poblacion_vs_actividades_localidad.py
py -3 notebooks/poblacion/priorizacion.py

# d) Mapas de calor -> outputs/mapas/
py -3 notebooks/poblacion/mapa.py
```

El paso (a) es imprescindible antes de (c) y (d): produce
`personas_Adultas_por_barrio_resumen.csv` y su equivalente de mayores. Esos CSV
todavía **no están versionados**, así que hay que generarlos primero.

`mapa.py` no descarga nada: lee la geometría de barrios ya versionada en
`data/processed/mapas/MapaPorBarriosBogota.json`.

### 4. Notas para quien retome el proyecto

Al reorganizar el repositorio se corrigieron tres errores que impedían ejecutar
el código:

1. Los dos `scrapper_sisben.py` usaban `CARPETA_DESCARGAS`, una variable que
   nunca se definía, y cualquier descarga del grid moría con `NameError`.
2. `scrappers/adultos/scrapper_sisben.py` armaba la tabla final con la columna
   de valor repetida en vez de `total_personas_adultas_raw`, que es la que
   `mapa.py` exige. El mapa de población adulta no se podía generar.
3. `poblacion_vs_presupuesto_localidad.py` buscaba `PoblacionAdultaBarrio.csv` y
   `PoblacionMayorBarrio.csv`, nombres que ningún script produce.

`viz.py` genera catorce figuras, pero cinco dependen de módulos que todavía no
están en el repositorio (`riesgo`, `cruce`, `oferta`, `equidad`,
`scrape_60mas`). Cuando falta el CSV de entrada, la figura se salta con un aviso
y el script sigue. Tres de esos CSV sí están versionados en
`data/processed/presupuesto/`, así que esas figuras salen igual; las que
dependen de `matriz_equidad.csv` y `brecha_catalogo_60mas.csv` no.

# Librerias usadas forma de instalar

Todas están fijadas en [requirements.txt](requirements.txt). Se instalan de una
sola vez:

```bash
py -3 -m pip install -r requirements.txt
py -3 -m playwright install chromium     # solo para los scrappers
```

| Librería | Para qué se usa |
|---|---|
| `pandas` | Toda la manipulación de tablas |
| `numpy` | Operaciones vectoriales del índice de priorización |
| `scipy` | Correlación de Pearson en `poblacion_vs_presupuesto_localidad.py` |
| `openpyxl` | Leer los `.xlsx` (`datos_por_localidad`, proyecciones UPL) |
| `odfpy` | Leer el `.ods` de proyecciones de población de la SDP |
| `matplotlib` | Todas las figuras PNG y SVG |
| `geopandas` | Cargar y cruzar la geometría de barrios |
| `shapely`, `pyproj`, `fiona` | Dependencias geoespaciales de `geopandas` |
| `folium` | Mapas de calor interactivos en HTML |
| `branca` | Escalas de color de los mapas |
| `requests` | Descargas de `download.py` y de la geometría de barrios |
| `playwright` | Automatiza el visor del Sisbén en los scrappers |

`geopandas`, `fiona` y `pyproj` traen binarios de GDAL. Si la instalación falla
en Windows, la vía más corta es un entorno de conda:

```bash
conda install -c conda-forge geopandas folium
```

# Problema

# Pregunta

# Metodologia
Busqueda del problema y fuentes asociadas
Analisis 



# Fuentes de Datos Usadas

Los datos vienen de cuatro orígenes:

- **[Mapa de Inversiones Bogotá](https://mapa-inversiones.gobiernoabiertobogota.gov.co/DatosAbiertos)** —
  presupuesto, proyectos de inversión y contratos del Distrito. Los perfiles de
  los dos proyectos de actividad física que se analizan son
  [8154 · Bogotá Deportiva](https://mapa-inversiones.gobiernoabiertobogota.gov.co/PerfilProyecto/8154)
  y [8155 · Programas recreativos y actividad física](https://mapa-inversiones.gobiernoabiertobogota.gov.co/PerfilProyecto/8155).
- **[Datos Abiertos Bogotá](https://datosabiertos.bogota.gov.co/)** — actividad
  física por localidad, proyecciones de población y geometrías oficiales.
- **[IDRD](https://www.idrd.gov.co/nuestros-programas)** — oferta de programas y
  programación de clases, por extracción manual.
- **[Visor Sisbén (SDP)](https://visorsisben.sdp.gov.co/)** — población por
  barrio, por scrapping.

Los archivos livianos están versionados en `data/`. Los pesados no: se regeneran
con `py -3 -m notebooks.presupuesto.download`.

# Principales Datos Granularidad y Fuente

CSV y EXCEL
| Nombre de la base de datos | Ubicación GitHub | Granularidad | Forma de obtener | Descripción y Uso |
|---|---|---|---|---|
| Datos Sisben | `data/processed/poblacion_adulta/`, `data/processed/poblacion_mayor/` (se genera) | Barrio | ScrapperSisben sobre el [visor](https://visorsisben.sdp.gov.co/) | Extraer los datos de personas adultas y mayores que habitan en determinado barrio. Insumo de `mapa.py`, `priorizacion.py` y los dos `poblacion_vs_*.py` |
| Encuesta Multipropósito - Actividad Física | [data/raw/EncuestaMultiproposito2021ActividadFisica.csv](data/raw/EncuestaMultiproposito2021ActividadFisica.csv) | Localidad | [Link](https://saludata.saludcapital.gov.co/osb/indicadores/proporcion-de-personas-que-realizan-actividad-fisica-en-bogota-d-c/) | Se encuentran índices de actividad física por localidad. `priorizacion.py` la usa como componente de sedentarismo |
| Proyecciones Poblacionales | No se versiona · `data/raw/sdp_poblacion_localidad.ods` | Localidad × edad × sexo | [Link](https://datosabiertos.bogota.gov.co/dataset/proyecciones-y-retroproyecciones-de-poblacion-2005-2035) · la baja `download.py` | Proyecciones poblacionales de Bogotá de 2005 a 2035. `poblacion.py` arma con ellas los denominadores (total, 15+, 45+, 60+) de todos los per cápita |
| Datos IDRD Localidad | [data/raw/datos_por_localidad.xlsx](data/raw/datos_por_localidad.xlsx) | Localidad | Extracción manual de [nuestros-programas](https://www.idrd.gov.co/nuestros-programas) y [escuelas deportivas adultos](https://www.idrd.gov.co/deportes/deporte-de-0-100/escuelas-deportivas-adultos) | Extracción manual de la oferta y presupuestos encontrados en la página del distrito. Cinco hojas: presupuesto por localidad, por categoría, ejecución, actividades por localidad y por escenario |
| Índice Priorización | `data/processed/poblacion_adulta/indice_prioridad_adulta.csv`, `data/processed/poblacion_mayor/indice_prioridad_mayor.csv` (se genera) | Barrio | CódigoPython — `priorizacion.py` | CSV creado cruzando los datos del Sisben, los datos del IDRD y la Encuesta Multipropósito para tener una lista de barrios a priorizar |
| Presupuesto General del Distrito | No se versiona · `data/raw/presupuesto_general.csv` | Entidad × mes | [Link](https://adlsinversionesbogota.blob.core.windows.net/opendata/DatosAbiertosPresupuestoGeneralDistrito.csv) · la baja `download.py` | Corte mensual de vigente, comprometido y girado. Es la fuente clave: `ejecucion.py` calcula con ella el % comprometido, el % girado y la concentración en diciembre |
| Proyectos de Inversión | No se versiona · `data/raw/proyectos_inversion.csv` | Proyecto × meta × actividad | [Link](https://adlsinversionesbogota.blob.core.windows.net/opendata/DatosAbiertosProyectosInversion.csv) · la baja `download.py` | Magnitudes programadas y entregadas. `desempeno.py` compara avance físico contra avance financiero |
| Contratos | No se versiona · `data/raw/contratos.csv` | Contrato | [Link](https://adlsinversionesbogota.blob.core.windows.net/opendata/DatosAbiertosContratos.csv) · la baja `download.py` | `contratos.py` busca menciones territoriales en el objeto contractual y mide en qué mes arranca cada peso contratado |
| Actividad Física - Enfermedades Crónicas (SDS) | Derivado versionado en [data/processed/presupuesto/riesgo_localidad.csv](data/processed/presupuesto/riesgo_localidad.csv) | Localidad | [Link](https://datosabiertos.bogota.gov.co/dataset/16025ea1-81cc-4947-b684-7a65303bb76b/resource/f5612407-9407-446c-b504-7ed1d21084ef/download/osb_enfermedadescronicas-actividadfisica.csv) · la baja `download.py` | Inactividad física 2017 vs. 2021 por localidad. Base del índice de riesgo que grafica `viz.py` |
| Oferta Escuelas Deportivas Adultos | Derivado versionado en [data/processed/presupuesto/oferta_escuelas_adultos.csv](data/processed/presupuesto/oferta_escuelas_adultos.csv) | Localidad | Extracción manual de la [programación publicada](https://www.idrd.gov.co/deportes/deporte-de-0-100/escuelas-deportivas-adultos) | Sesiones, escenarios y disciplinas por localidad. Es el único de los 14 programas del catálogo con horarios verificables |

MAPAS

| Nombre Mapa | Ubicación GitHub | Forma de Obtener | Descripción y Uso |
|---|---|---|---|
| Mapa Por Barrios Bogotá | [data/processed/mapas/MapaPorBarriosBogota.json](data/processed/mapas/MapaPorBarriosBogota.json) | [Link](https://datosabiertos.bogota.gov.co/dataset/sector-catastral) | Sector catastral enriquecido con `clave`, `barrio_norm` y `localidad_norm`. Es la geometría que `mapa.py` cruza con la población del Sisbén |
| Mapa Por Localidad Bogotá | [data/raw/mapas/MapaPorLocalidadBogota.json](data/raw/mapas/MapaPorLocalidadBogota.json) | [Link](https://datosabiertos.bogota.gov.co/dataset/localidad-bogota-d-c) | Límites por localidad, para el shapeMap del informe de Power BI |

# Hallazgos

# Contratacion

# Salud

# Poblacion y Barrios

# Power BI

# Conclusiones
