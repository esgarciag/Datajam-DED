# Diccionario de datos

Qué significa cada columna de las tablas de `data/processed/`. Es material de
consulta: las instrucciones para generarlas están en el
[README](../README.md).

Los valores monetarios están en **millones de pesos** salvo que la columna diga
otra cosa. Los porcentajes van de 0 a 100, no de 0 a 1.

---

## Llave territorial

Todas las tablas por localidad comparten las mismas dos columnas, y ese es el
punto de unión entre los dos bloques del proyecto:

| Columna | Tipo | Descripción |
|---|---|---|
| `cod_localidad` | entero 1–20 | Código oficial de localidad (Decreto 1421/93) |
| `localidad` | texto | Nombre canónico, con tildes: `Usaquén`, `Ciudad Bolívar`, … |

En `notebooks/presupuesto/` la equivalencia la resuelve `localidades.py` con la
función `normalizar()`. En `notebooks/poblacion/` cada script arma además
`clave = localidad_norm + "_" + barrio_norm`, en mayúsculas y sin tildes, porque
trabaja a nivel de barrio.

---

## Ejecución presupuestal

### `ejecucion_idrd_mensual.csv` · `ejecucion_fdl_mensual.csv`

Serie mensual del Presupuesto General del Distrito. La del IDRD es por
institución; la de los Fondos de Desarrollo Local es por localidad.

| Columna | Descripción |
|---|---|
| `anio`, `mes` | Periodo del corte |
| `ValorVigente` | **Stock**: presupuesto aprobado a esa fecha |
| `ValorCompromiso` | **Acumulado dentro del año**: se reinicia en enero |
| `ValorGiros` | Acumulado dentro del año, misma lógica |
| `giro_mes` | Flujo del mes: diferencia del acumulado contra el mes anterior |
| `compromiso_mes` | Ídem para compromisos |

> Confundir el acumulado con el flujo es el error más fácil de cometer con esta
> fuente. `ValorGiros` de diciembre es el total del año, no lo girado en
> diciembre; eso es `giro_mes`.

### `ejecucion_idrd_anual.csv` · `ejecucion_fdl_anual.csv`

Cierre de cada año, con los tres indicadores que el análisis distingue.

| Columna | Descripción |
|---|---|
| `mes_corte` | Último mes con dato de ese año |
| `vigente`, `comprometido`, `girado` | Valores al cierre |
| `pct_comprometido` | comprometido / vigente. Mide si se logró **contratar** la plata |
| `pct_girado` | girado / vigente. Mide si la plata efectivamente **salió** |
| `pct_girado_de_comprometido` | Cuánto de lo contratado se pagó |
| `giro_diciembre`, `giro_q4` | Giros del último mes y del último trimestre |
| `concentracion_diciembre` | giros de diciembre / giros del año. Referencia neutra: 1/12 = 8,3% |
| `concentracion_q4` | Ídem para el trimestre. Referencia neutra: 25% |
| `anio_completo` | `True` si el año tiene los 12 cortes; si es `False`, los porcentajes no son comparables |

Un `pct_girado` alto con `concentracion_diciembre` alta describe un año que
cerró bien en el papel pero ejecutó tarde.

---

## Contratación

### `contratos_af_idrd.csv`

Una fila por contrato de los proyectos 8154 y 8155.

| Columna | Descripción |
|---|---|
| `CodigoContrato`, `CodigoBPIN` | Identificadores del contrato y del proyecto |
| `Contratista`, `Comprador` | Partes |
| `ValorPlaneado`, `ValorContratado` | Valores del contrato |
| `FechaInicioContrato`, `FechaFinContrato` | Vigencia |
| `proyecto` | `8154 · Bogotá Deportiva` o `8155 · Programas recreativos y actividad física` |

### `contratos_calendario.csv` · `contratos_calendario_tipo.csv` · `contratos_calendario_referencia.csv`

Distribución del valor contratado según el mes de inicio. `tipo_objeto` separa
lo que es actividad física directa de lo que es infraestructura; `ambito`
permite contrastar el IDRD contra el resto del Distrito.

### `contratos_timing.csv`

Resumen por año, tres filas.

| Columna | Descripción |
|---|---|
| `contratos`, `valor_mm` | Cuántos y por cuánto |
| `pct_inicia_Q1` | % del valor que arranca en el primer trimestre |
| `pct_inicia_Q4` | % que arranca en el último |
| `mes_pico`, `pct_en_mes_pico` | Mes que concentra más valor, y cuánto |

Un programa de actividad física que arranca en noviembre no alcanza a producir
el efecto poblacional que promete su meta anual: para eso está esta tabla.

---

## Desempeño

### `desempeno_proyectos.csv` · `desempeno_actividades_af.csv`

Avance físico contra avance financiero. Son cosas distintas y se confunden a
menudo: una entidad puede girar el 100% y entregar la mitad de las metas.

| Columna | Descripción |
|---|---|
| `actividades` | Número de actividades del proyecto |
| `programado_mm` | Valor programado |
| `avance_fisico` | magnitud entregada / magnitud programada, en %, tope 300 |
| `avance_financiero` | valor girado / valor programado, en % |
| `actividades_en_cero` | Actividades con magnitud entregada = 0 |
| `brecha_vs_tiempo` | `avance_fisico` menos el % del cuatrienio ya transcurrido. Negativo = atrasado |

> Las magnitudes las reporta la propia entidad y no hay verificación
> independiente: miden lo que la entidad **dice** que entregó.

---

## Población

### `poblacion_localidad_2025.csv` · `poblacion_localidad_proyeccion.csv`

Denominadores de todos los per cápita. La primera es el corte de 2025; la
segunda trae la serie.

| Columna | Descripción |
|---|---|
| `poblacion_total` | Toda la población de la localidad |
| `poblacion_15_mas` | En edad de hacer actividad física de forma autónoma |
| `poblacion_45_mas` | Ventana donde se materializa el riesgo cardiometabólico |
| `poblacion_60_mas` | Persona mayor: público de Pasaporte Vital |
| `pct_45_mas`, `pct_60_mas` | Peso de cada grupo sobre el total |

---

## Riesgo y oferta

### `riesgo_localidad.csv`

Índice de riesgo por localidad, a partir de la Encuesta Multipropósito 2017 y
2021.

| Columna | Descripción |
|---|---|
| `nada_2017`, `nada_2021` | % que no practicó deporte ni actividad física en el mes |
| `3omas_sem_2017`, `3omas_sem_2021` | % que se ejercita 3 o más veces por semana |
| `delta_nada`, `delta_3omas` | Cambio entre 2017 y 2021. `delta_nada` positivo = empeoró |
| `c_nivel` | Componente: cuánta gente no hace nada de ejercicio |
| `c_deficit` | Componente: cuánta gente no llega al mínimo recomendado |
| `c_deterioro` | Componente: cuánto empeoró entre 2017 y 2021 |
| `indice_riesgo` | Combinación ponderada de los tres, 0–100 |
| `rank_riesgo` | 1 = mayor riesgo |

### `oferta_escuelas_adultos.csv`

Oferta real de Escuelas Deportivas Adultos, cruzada con población y riesgo.

| Columna | Descripción |
|---|---|
| `sesiones`, `escenarios`, `disciplinas` | Programación publicada por localidad |
| `sesiones_barrera_alta` | Sesiones con requisitos que limitan el acceso |
| `sesiones_base` | Sesiones sin esa barrera |
| `hab15_por_sesion` | Habitantes de 15+ por sesión semanal. Vacío = no hay sesiones |

Una localidad con `sesiones = 0` y `rank_riesgo` bajo es exactamente el caso que
el análisis busca: mucha necesidad, nada de oferta.

### `inversion_af_localidad.csv`

| Columna | Descripción |
|---|---|
| `*_af_directa` | Programas de actividad física: clases, monitores, eventos |
| `*_af_infra` | Infraestructura: parques de proximidad, escenarios |
| `af_total_programado`, `af_total_girado` | Suma de ambas líneas |
| `pct_girado_af`, `pct_comprometido_af` | Ejecución de la inversión en actividad física |

### `cruce_final.csv`

Une riesgo, inversión, población y oferta en una fila por localidad. Es la tabla
de la que salen las figuras de cuadrantes y de brecha.

| Columna | Descripción |
|---|---|
| `af_pc`, `af_directa_pc`, `af_pc_45mas` | Inversión per cápita, con distintos denominadores |
| `rank_inversion` | 1 = más inversión per cápita |
| `brecha_rank` | `rank_inversion` menos `rank_riesgo`. Positivo = recibe menos de lo que su riesgo justificaría |
| `sesiones_pc_100k` | Sesiones por cada 100.000 habitantes de 15+ |
| `brecha_servicio` | Déficit de oferta frente al riesgo de la localidad |
| `diagnostico` | Etiqueta resumen del cuadrante en que cae la localidad |

---

## Población por barrio

### `personas_Adultas_por_barrio_resumen.csv` · `personas_Mayores_por_barrio_resumen.csv`

Salida directa del scrapper del visor del Sisbén.

| Columna | Descripción |
|---|---|
| `localidad`, `barrio` | Territorio, tal como los nombra el visor |
| `total_personas_adultas` / `total_personas_mayores` | Conteo, ya convertido a número |
| `..._raw` | El valor original del visor, antes de limpiar separadores de miles |

La fila con `barrio = "Todos"` es el total de la localidad, no un barrio: los
scripts la descartan.

### `PoblacionAdultaBarrioNormalizado.csv` · `PoblacionMayorBarrioNormalizado.csv`

Lo mismo, separado por tabulaciones y con la llave de cruce añadida.

| Columna | Descripción |
|---|---|
| `barrio_norm`, `localidad_norm` | Mayúsculas, sin tildes |
| `clave` | `localidad_norm + "_" + barrio_norm`. Es la llave de todos los joins por barrio |

### `indice_prioridad_adulta.csv` · `indice_prioridad_mayor.csv`

Índice de prioridad de inversión por barrio, en escala 0–100.

| Columna | Descripción |
|---|---|
| `clave`, `localidad`, `barrio` | Llave y territorio, heredados del CSV de población |
| `total_personas_adultas` / `total_personas_mayores` | Población del barrio |
| `pct_sedentarismo` | % de la localidad que no practicó actividad física (Encuesta Multipropósito) |
| `clases_por_semana`, `escenarios_con_clases` | Oferta IDRD de la localidad |
| `presupuesto_girado_millones`, `pct_girado` | Ejecución IDRD de la localidad |
| `indice_prioridad` | 0–100, dos decimales |
| `ranking_prioridad` | 1 = barrio más prioritario |

El índice se calcula con cuatro componentes normalizados 0–1 por min–max. Esas
columnas normalizadas son intermedias y **no** quedan en el CSV:

| Componente | Peso | Signo |
|---|---|---|
| Sedentarismo de la localidad | 0,35 | **+** más sedentarismo = más prioridad |
| Población del barrio | 0,25 | **+** más población = más prioridad |
| Clases por cada 10.000 habitantes | 0,20 | **−** más oferta = menos prioridad |
| Presupuesto girado por cada 10.000 habitantes | 0,20 | **−** más ejecución = menos prioridad |

El sedentarismo, la oferta y la ejecución vienen a nivel de localidad, así que
todos los barrios de una misma localidad comparten esos tres componentes. Lo
único que diferencia a un barrio de su vecino es la población.

### `presupuesto_vs_poblacion_adulta.csv` · `presupuesto_vs_poblacion_mayor.csv`

Una fila por localidad. Alimenta la dispersión con su correlación de Pearson.

| Columna | Descripción |
|---|---|
| `Localidad` | Nombre tal como viene de `datos_por_localidad.xlsx` |
| `total_personas_adultas` / `total_personas_mayores` | Población de la localidad, sumada desde los barrios |
| `Total programado (millones)`, `Total girado (millones)` | Presupuesto IDRD |
| `% girado` | girado / programado |
| `presupuesto_programado_por_persona` | El per cápita que compara localidades |

### `clases_vs_poblacion_adulta.csv` · `clases_vs_poblacion_mayor.csv`

Misma estructura, contra oferta en vez de presupuesto.

| Columna | Descripción |
|---|---|
| `Clases por semana`, `Escenarios con clases`, `Disciplinas distintas` | Oferta IDRD de la localidad |
| `clases_por_1000_personas` | Clases semanales por cada 1.000 personas del grupo |
| `escenarios_por_1000_personas` | Ídem para escenarios |
