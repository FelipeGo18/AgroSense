# Backlog

Índice de todas las historias de usuario. Fuente de verdad: los archivos de `specs/epicas/`. Cuando una HU cambie de estado, se actualiza en su archivo de épica y aquí.

> **Recorte del MVP (11 de octubre de 2026, decisión 12):** P0 es el MVP. Lo que no sirve al flujo principal (lote o municipio y área → estrategias de rotación → un ciclo con su diagnóstico → agua del plan → qué cambió) pasó a P1. Las HU que cambiaron llevan en la columna «Nota» «Pasó a P1 el 11 de octubre de 2026: recorte del MVP», «Reducida» o «Nueva». Totales y horas en `docs/plan-48h.md`.

| Épica | HU | Título | Prio | Tamaño | Estado | Nota |
|---|---|---|---|---|---|---|
| [EP-00](epicas/EP-00-alcance.md) | HU-001 | Comparar la cobertura de EVA y elegir región | P0 | M | pendiente | |
| [EP-00](epicas/EP-00-alcance.md) | HU-002 | Confirmar los datasets NASA del enunciado | P0 | S | hecha | Datos de la NASA documentados y probados sobre Duitama (12 nov); pestaña de recursos revisada (13 nov): nada cambia el núcleo; ERA5 y GLDAS, en P1, como contraste |
| [EP-00](epicas/EP-00-alcance.md) | HU-003 | Verificar SIPSA y decidir si entra al P0 | P0 | S | hecha | Verificado y mapeado (7 nov): SIPSA cubre papa, arveja, cebolla de bulbo y zanahoria. Entra, aprobado por Felipe (10 nov) |
| [EP-00](epicas/EP-00-alcance.md) | HU-004 | Confirmar qué se puede preparar antes del evento | P0 | S | hecha | Sí se puede llevar código (8 nov); los términos 2026 no limitan cuándo se crea el trabajo, pero piden licencia OSI, licencias de terceros documentadas y citar todas las fuentes (10 nov) |
| [EP-01](epicas/EP-01-contratos.md) | HU-011 | Esquema de las tablas publicadas | P0 | M | hecha | `pipeline/schema.py` y los ejemplos en `data/examples/` (8 nov) |
| [EP-01](epicas/EP-01-contratos.md) | HU-012 | OpenAPI con ejemplos de cada estado | P0 | M | hecha | Modelos y ejemplos de los endpoints de cálculo; responden 501 hasta su HU del motor (8 nov) |
| [EP-01](epicas/EP-01-contratos.md) | HU-013 | Respuestas simuladas (MSW) | P0 | S | hecha | `VITE_SIMULATION=true` y `?estado=`; generadas del OpenAPI con `npm run api:examples` (9 nov) |
| [EP-01](epicas/EP-01-contratos.md) | HU-014 | Modo simulación para desarrolladores | P1 | M | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-02](epicas/EP-02-base-desplegada.md) | HU-021 | Clonar y ejecutar con pocos comandos | P0 | S | hecha | Probado con y sin Docker en dos máquinas (`docs/reporte-prueba-hu-021.md`) |
| [EP-02](epicas/EP-02-base-desplegada.md) | HU-022 | Lint y pruebas automáticas en cada cambio | P0 | S | hecha | Corre el comando de test con `docker compose run --rm test` para Ruff, Ruff format, pytest y web |
| [EP-02](epicas/EP-02-base-desplegada.md) | HU-177 | Logs de la terminal | P0 | S | en curso | Hecho para la API, las migraciones y el pipeline (8 nov); falta lo de los endpoints de cálculo, que aún no existen |
| [EP-02](epicas/EP-02-base-desplegada.md) | HU-023 | Esqueleto desplegado en URL pública | P0 | M | pendiente | Con la base de datos en la nube (10 nov) |
| [EP-02](epicas/EP-02-base-desplegada.md) | HU-229 | Migraciones revisadas y aplicadas con GitHub Actions | P0 | M | en curso | Nueva (10 nov) |
| [EP-03](epicas/EP-03-oferta-eva.md) | HU-031 | Datos de EVA normalizados por DIVIPOLA | P0 | M | pendiente | |
| [EP-03](epicas/EP-03-oferta-eva.md) | HU-032 | Variación del área sembrada y participación departamental | P0 | M | pendiente | |
| [EP-03](epicas/EP-03-oferta-eva.md) | HU-200 | Siembras registradas en AgroSense como dato de oferta | P1 | M | pendiente | |
| [EP-03](epicas/EP-03-oferta-eva.md) | HU-201 | Fuentes de contraste para la oferta | P1 | M | pendiente | |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-041 | Series diarias de lluvia y temperatura | P0 | M | hecha | Adaptador de NASA POWER con caché por celda (20 celdas) y `climate_day` corregida por altitud, publicada con la de NASADEM (HU-206) |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-042 | Lluvia mensual y su normal | P0 | M | hecha | `climate_month` con la lluvia de NASA POWER y su normal 1991–2020; en el altiplano es de 1,7 a 2,7 veces la del IDEAM (riesgo para la señal de agua) |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-205 | NASA POWER ampliado: humedad, radiación y viento | P0 | M | hecha | Humedad del suelo, radiación (desde 1984), viento y humedad relativa en la caché; la humedad del suelo, en `climate_month` |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-206 | Altitud de municipios y lotes con NASADEM | P0 | M | hecha | `grid_cells` con altitud y pendiente de NASADEM; la altitud del municipio es la de la celda de la cabecera y su pendiente, la mediana (decidido por Felipe) |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-207 | Lluvia por satélite con GPM IMERG | P0 | L | hecha | `precip_month` con IMERG mensual V07; `water` usa IMERG con el aviso de que sobrestima en el altiplano (1,85 veces el IDEAM) y POWER de contraste (decidido por Felipe) |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-208 | Verdor del campo por municipio con MODIS NDVI | P0 | L | pendiente | Nueva |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-209 | Verdor por lote con MODIS NDVI | P1 | M | pendiente | Pasó a P1 el 8 de noviembre de 2026 (decisión 15): toda la región serían unos 14 millones de filas |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-210 | Humedad del suelo por satélite con SMAP | P0 | M | pendiente | Ya no es lo primero que se recorta: el reto lo nombra primero (decisión 14) |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-216 | Clima de dos periodos para «Qué cambió» | P0 | M | pendiente | Nueva |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-044 | Municipios, límites, altitud y corrección de la temperatura | P0 | S | hecha | Municipios de DIVIPOLA, límites del MGN, altitud de NASADEM, altura de la celda de NASA POWER y temperatura media anual publicadas; temperaturas corregidas con el gradiente de `region.yaml`; comprobado contra 4 estaciones del IDEAM: queda un sesgo de POWER entre el día y la noche (ver HU-045) |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-045 | Heladas y temperatura máxima por mes | P0 | M | hecha | `climate_risk_month` y `climate_frost_month` con la mínima ≤ 2 °C (ZARC); la helada cae en enero, pero POWER cuenta muchas menos de las que mide el IDEAM |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-193 | Riesgo climático por semana | P1 | M | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-043 | Verdor por lote con HLS (30 m) | P1 | L | pendiente | Antes «Humedad del suelo y NDVI» |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-046 | Aguaceros, ventanas secas y gota por mes | P1 | M | pendiente | |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-188 | Riesgos que cubre un seguro, por municipio | P1 | S | pendiente | |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-189 | Lluvia en años de El Niño y La Niña | P1 | M | pendiente | |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-225 | Tendencia del agua almacenada con GRACE-FO | P1 | M | pendiente | Nueva (8 nov, decisión 14) |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-226 | Temperatura de la superficie y evapotranspiración con ECOSTRESS | P1 | M | pendiente | Nueva (8 nov, decisión 14) |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-231 | Heladas de ERA5-Land para contrastar las de NASA POWER | P1 | M | pendiente | Nueva (13 nov, recursos del reto): POWER casi no ve heladas en el altiplano |
| [EP-04](epicas/EP-04-clima-nasa.md) | HU-232 | Humedad del suelo de GLDAS para contrastar | P1 | S | pendiente | Nueva (13 nov, recursos del reto) |
| [EP-05](epicas/EP-05-mercado-sipsa.md) | HU-051 | Índice estacional de precio | P1 | M | hecha | `market_month` publicada (7 nov); columnas y mapeo aprobados por Felipe (10 nov); el maíz queda sin producto |
| [EP-05](epicas/EP-05-mercado-sipsa.md) | HU-221 | Precios en la central de abastos | P1 | L | en curso | Contrato aprobado por Felipe (10 nov). Falta el diseño en Figma |
| [EP-05](epicas/EP-05-mercado-sipsa.md) | HU-222 | Precios al día | P1 | M | hecha | Dos crons del servicio `market` (9 nov): boletín diario y serie completa semanal; la API solo lee. Contrato aprobado por Felipe (10 nov) |
| [EP-06](epicas/EP-06-catalogo-agronomico.md) | HU-061 | Ficha por cultivo | P0 | M | en curso | Fichas de los 7 cultivos y el descanso con fuente por valor; falta revisión cruzada |
| [EP-06](epicas/EP-06-catalogo-agronomico.md) | HU-199 | Límites óptimos y absolutos de cada cultivo | P0 | M | en curso | Rangos de EcoCrop y UPRA con validación; falta revisión cruzada |
| [EP-06](epicas/EP-06-catalogo-agronomico.md) | HU-198 | Pesos por defecto con su porqué | P0 | S | en curso | Archivo con pesos provisionales y `GET /version`; falta la propuesta de Producto y agro y su aprobación |
| [EP-06](epicas/EP-06-catalogo-agronomico.md) | HU-062 | Reglas de rotación como datos | P0 | M | pendiente | Suma la salud del suelo |
| [EP-06](epicas/EP-06-catalogo-agronomico.md) | HU-063 | Suelo, heladas y abonos verdes en el catálogo | P0 | M | en curso | pH con fuente; helada y calor por etapa con fuente desde HU-142 (14 nov); faltan los abonos verdes y el descanso con sus reglas, las reglas de suelo y la revisión cruzada |
| [EP-06](epicas/EP-06-catalogo-agronomico.md) | HU-227 | Valor como forraje en el catálogo | P1 | S | pendiente | Nueva (8 nov, decisión 14) |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-071 | Señal de agua | P0 | M | pendiente | Suma IMERG y la humedad del suelo |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-072 | Señal de oferta | P0 | M | pendiente | |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-073 | Señal de mercado sin datos | P0 | S | pendiente | |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-196 | Calificación de las señales con curvas por cultivo | P0 | M | hecha | `score_signal` en `backend/engine/signal_score.py` con la curva de `curve.py`: agua y heladas con los puntos de `thresholds.yaml`, calor y suelo con la ficha; oferta y mercado sin datos mientras no tengan curva (13 nov) |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-074 | Semáforo con prioridades, dos luces y acción | P0 | L | pendiente | |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-197 | Cultivos alternativos con mejor oferta | P1 | M | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-077 | Señal de heladas | P0 | M | pendiente | Por mes en el MVP |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-190 | Señal de calor | P0 | M | pendiente | Por mes en el MVP |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-191 | Aptitud del cultivo en la zona | P0 | M | en curso | Por temperatura media anual desde el 16 oct (decisión 13); con lote, corregida a su altitud. Motor y caso `not_suitable` de `/diagnostics` listos (PR #56); desde el 13 nov la API calcula la altitud del lote y corrige la temperatura con el gradiente del manifiesto (primer criterio hecho); faltan el caso `suitable`/`insufficient_data` (esperan las señales) y el cableado en `/rotations` y `/changes` |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-192 | Orden de las ventanas por factor limitante y prioridades | P0 | M | pendiente | |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-075 | Umbrales y pesos versionados | P0 | S | en curso | `weights.yaml` y `thresholds.yaml` 1.0.0 hechos (10 nov); oferta y mercado sin fuente. Falta lo que depende del motor |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-076 | Endpoint de diagnóstico con errores claros | P0 | S | pendiente | |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-078 | Endpoints de catálogo y tendencias | P0 | S | en curso | `/municipalities`, `/boundary` y `/crops` hechos; faltan suelo y `/trends` |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-217 | Comparar dos periodos de la historia de la zona | P0 | M | pendiente | Nueva |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-218 | Endpoint de «Qué cambió» | P0 | S | pendiente | Nueva |
| [EP-07](epicas/EP-07-diagnostico.md) | HU-195 | Señales de exceso de lluvia, enfermedad y cosecha | P1 | M | pendiente | |
| [EP-08](epicas/EP-08-rotaciones.md) | HU-081 | Filtrar estrategias válidas | P0 | M | pendiente | Estrategias de hasta 3 ciclos |
| [EP-08](epicas/EP-08-rotaciones.md) | HU-213 | Ciclos de una estrategia con su diagnóstico | P0 | M | pendiente | Nueva |
| [EP-08](epicas/EP-08-rotaciones.md) | HU-082 | Ordenar estrategias por prioridades | P0 | M | pendiente | Estrategias de hasta 3 ciclos |
| [EP-08](epicas/EP-08-rotaciones.md) | HU-083 | Explicar el orden de las estrategias | P0 | S | pendiente | |
| [EP-08](epicas/EP-08-rotaciones.md) | HU-084 | Endpoint de estrategias de rotación | P0 | S | pendiente | Suma `current_crop_ids` (decisión 14) |
| [EP-08](epicas/EP-08-rotaciones.md) | HU-223 | La rotación actual como referencia | P0 | M | pendiente | Nueva (8 nov, decisión 14): el reto pide comparar contra la actual |
| [EP-09](epicas/EP-09-web-diagnostico.md) | HU-091 | Elegir municipio, cultivo y cuándo sembrar | P0 | M | hecha | En `/diagnostico`; la consulta va en la dirección; con lote, municipio y riego del lote (10 nov) |
| [EP-09](epicas/EP-09-web-diagnostico.md) | HU-092 | Semáforo con señales, razones y limitaciones | P0 | M | hecha | Seis señales con calificación, «Lo que más limita», fuentes y limitaciones; rótulo de la cosecha según `harvest_basis` (10 nov) |
| [EP-09](epicas/EP-09-web-diagnostico.md) | HU-194 | Cultivo no apto y mejores ventanas | P0 | S | hecha | Letrero de no apto con nota y semillas; mejores fechas que consultan esa fecha; sin ventanas, el enlace a estrategias (10 nov). Alternativas P1 |
| [EP-09](epicas/EP-09-web-diagnostico.md) | HU-202 | Ajustar mis prioridades al consultar | P0 | S | hecha | Controles, `priorities`, todo en 0 y guardado (navegador o perfil) (10 nov); se envían como `signal_priorities` a las estrategias (11 nov, HU-214). Lo de HU-180 es P1 |
| [EP-09](epicas/EP-09-web-diagnostico.md) | HU-203 | Dos luces y cultivos alternativos | P0 | M | hecha | Una o dos luces con su acción, lo que más limita y por qué difieren; «No cuenta» y «Cuenta siempre»; enlace a estrategias (10 nov). Las alternativas son P1 |
| [EP-09](epicas/EP-09-web-diagnostico.md) | HU-093 | Gráfica de la lluvia de la ventana | P0 | S | hecha | En la señal de agua del diagnóstico y del ciclo, con la fuente, los años sin lluvia suficiente y su tabla (11 nov). Reducida a una gráfica (antes M) |
| [EP-09](epicas/EP-09-web-diagnostico.md) | HU-094 | Estados de carga, vacío y error | P0 | S | en curso | Esqueleto sin cifras ficticias; tarjetas de sin conexión, fecha inválida, lote inexistente y errores de la API, con acciones de recuperación y código de soporte para fallos del servidor. Queda pendiente estado sin cobertura por falta de código propio en el contrato (decidido por Felipe el 13 de noviembre de 2026: no por ahora) |
| [EP-09](epicas/EP-09-web-diagnostico.md) | HU-219 | Pantalla «Qué cambió en su zona» | P0 | M | pendiente | Nueva |
| [EP-09](epicas/EP-09-web-diagnostico.md) | HU-095 | Mapa regional por semáforo | P1 | L | pendiente | |
| [EP-09](epicas/EP-09-web-diagnostico.md) | HU-096 | Uso desde el celular | P0 | S | hecha | Toda la web revisada: 25 pantallas en 11 tamaños, con y sin modo ligero, 550 de 550; dos enlaces agrandados (12 nov) |
| [EP-10](epicas/EP-10-web-rotaciones.md) | HU-214 | Entrada a las estrategias, con o sin cuenta | P0 | M | hecha | En `/consultar`, con o sin lote; el área sin cuenta queda en el navegador; un resumen hasta HU-102 (11 nov) |
| [EP-10](epicas/EP-10-web-rotaciones.md) | HU-101 | Prioridades del agricultor | P0 | S | hecha | Cuatro controles que empiezan en 3; con todas en 0 no se consulta (11 nov, con HU-214) |
| [EP-10](epicas/EP-10-web-rotaciones.md) | HU-102 | Estrategias con ciclos, desglose y salud del suelo | P0 | L | hecha | Tarjetas, desglose, lo de hoy, salud del suelo con fuente, descartadas y estado vacío; cada ciclo abre su detalle (11 nov). Antes M |
| [EP-10](epicas/EP-10-web-rotaciones.md) | HU-215 | Ciclo de una estrategia | P0 | M | hecha | Diagnóstico del ciclo con las piezas del diagnóstico, agua por mes, humedad de la zona, verdor y registrar el primer ciclo (11 nov) |
| [EP-11](epicas/EP-11-escenarios.md) | HU-111 | Reevaluar con cambios en memoria | P1 | M | pendiente | |
| [EP-11](epicas/EP-11-escenarios.md) | HU-112 | Endpoint de escenarios | P1 | S | pendiente | |
| [EP-11](epicas/EP-11-escenarios.md) | HU-113 | Comparación de escenarios | P1 | M | pendiente | |
| [EP-12](epicas/EP-12-calidad-trazabilidad.md) | HU-121 | Casos de referencia del motor | P0 | L | pendiente | Suma estrategias y «Qué cambió» |
| [EP-12](epicas/EP-12-calidad-trazabilidad.md) | HU-122 | Procedencia de cada dato | P0 | S | en curso | Manifiesto, `sources`, `/version` y `catalog/sources.yaml` (11 nov, lluvia de POWER temporal con aviso); faltan las fuentes NASA sin adaptador y la web |
| [EP-12](epicas/EP-12-calidad-trazabilidad.md) | HU-123 | Reconstruir el dataset con un comando | P0 | S | hecha | `pipeline.build` publica y revisa contra el manifiesto; `--verificar` solo revisa (8 nov) |
| [EP-13](epicas/EP-13-demo-entrega.md) | HU-131 | Dos casos reales para la demo | P0 | S | pendiente | |
| [EP-13](epicas/EP-13-demo-entrega.md) | HU-132 | Video y descripción de la entrega | P0 | M | pendiente | |
| [EP-13](epicas/EP-13-demo-entrega.md) | HU-133 | Impacto económico, social y ambiental | P0 | S | pendiente | |
| [EP-13](epicas/EP-13-demo-entrega.md) | HU-230 | Licencias del proyecto y de lo que usa | P0 | S | en curso | Nueva (10 nov). `LICENSE` Apache 2.0 hecho; falta la lista de licencias de terceros para la entrega |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-142 | Etapas de cada cultivo con Kc | P0 | S | hecha | Los 7 cultivos del MVP. Helada y calor por etapa, cada valor con su fuente, y el calor del maíz en 35 °C (14 nov, dataset 2026.11.14); revisión cruzada de Luisa (PR #69) |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-220 | Etapas de una ventana por calendario | P0 | S | hecha | `crop_window`: etapas, meses y meses sensibles de una ventana (10 nov). La helada y el calor por etapa están en el catálogo desde HU-142 (14 nov), con nulos donde no hay fuente |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-143 | Lluvia y ET0 mensuales por municipio | P0 | M | hecha | ET0 por Penman-Monteith de FAO-56 (`pipeline/et0.py`), su normal y el año seco (percentil 20, decidido por Felipe) en `climate_month` |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-144 | Déficit de agua por cultivo y etapa | P0 | M | pendiente | |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-146 | Endpoint del plan de agua | P0 | S | pendiente | |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-141 | Registrar la finca | P1 | M | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-145 | Calendario de riego de la finca | P1 | M | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-150 | Etapa del cultivo por temperatura acumulada | P1 | M | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-179 | Calendario del cultivo | P1 | M | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-180 | Vista del calendario | P1 | M | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-186 | Línea de tiempo del cultivo | P1 | M | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-147 | Aviso de riego semanal | P1 | L | pendiente | |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-148 | Rotaciones ponderadas por área | P1 | S | pendiente | |
| [EP-14](epicas/EP-14-finca-agua.md) | HU-149 | Guardar la finca en el dispositivo | P1 | S | pendiente | |
| [EP-15](epicas/EP-15-identidad-prototipo.md) | HU-151 | Moodboard y dirección visual | P0 | S | hecha | |
| [EP-15](epicas/EP-15-identidad-prototipo.md) | HU-152 | Tokens de diseño | P0 | M | hecha | |
| [EP-15](epicas/EP-15-identidad-prototipo.md) | HU-153 | Kit de componentes con estilo de juego | P0 | L | hecha | |
| [EP-15](epicas/EP-15-identidad-prototipo.md) | HU-154 | Escena 3D del paisaje andino | P1 | L | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-15](epicas/EP-15-identidad-prototipo.md) | HU-155 | Descenso de cámara del satélite al lote | P1 | L | en curso | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-15](epicas/EP-15-identidad-prototipo.md) | HU-156 | Sistema de motion | P1 | M | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-15](epicas/EP-15-identidad-prototipo.md) | HU-157 | Audio de ambiente e interfaz | P1 | M | pendiente | |
| [EP-15](epicas/EP-15-identidad-prototipo.md) | HU-158 | Modo ligero y movimiento reducido | P0 | M | en curso | GSAP y Lenis se cargan aparte: en modo ligero el JS inicial baja de 197 a 149 kB; verificados sin WebGL y con «reducir movimiento» (12 nov). Falta el Figma y el paso a 2D de la escena 3D (P1) |
| [EP-15](epicas/EP-15-identidad-prototipo.md) | HU-159 | Prototipo navegable con datos de ejemplo | P1 | L | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-160 | Editar mi perfil y cambiar la contraseña | P1 | S | hecha | Backend, pantallas y «Sus prioridades» hechos; revisión de seguridad hecha. Cerrada el 10 de noviembre de 2026 |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-178 | Trazabilidad de lo que hacen agricultores y administradores | P1 | M | en curso | Tabla, eventos de la cuenta y «Mi actividad» hechos; revisión de seguridad hecha y limpieza de 180 días al arrancar; faltan los permisos de solo agregar y la limpieza con otro rol |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-170 | Roles: agricultor, administrador y desarrollador | P1 | L | pendiente | |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-161 | Esquema de cuentas y migraciones | P0 | M | hecha | Esquema completo del contrato; `municipality_id` y `crop_id` se validan contra el catálogo publicado. Cerrada el 10 de noviembre de 2026 |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-162 | Autenticación | P0 | L | hecha | Backend y pantallas hechos; revisión de seguridad hecha y arreglada; entrar y la sesión vencida no escriben de más (PR #19 y #20). Cerrada el 10 de noviembre de 2026 |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-163 | Consentimiento y tratamiento de datos | P0 | S | en curso | Página de la política hecha, con el aviso de que falta la revisión legal; falta esa revisión y el canal de contacto |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-164 | Lotes del usuario | P0 | L | en curso | Entregas 1 y 2: lotes dibujados en el mapa o con el área a mano; «Ver estrategias» desde el lote (11 nov); «Borrar este lote» con confirmación, probado (12 nov); falta el riego del lote en el motor |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-165 | Temporadas e historial del lote | P0 | L | en curso | Entrega 3: API y pantallas de siembra, cosecha y corregir; falta pasar el historial a las estrategias (EP-08) |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-204 | Historial con lo borrado y «Restaurar» | P1 | S | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-166 | Borrar mi cuenta | P0 | S | hecha | `DELETE /me` con la contraseña, borrado en cascada probado y confirmación en Mi cuenta. Cerrada el 10 de noviembre de 2026 |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-167 | Progreso del lote | P1 | S | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-168 | Registro, sesión y paso de invitado a cuenta | P0 | M | pendiente | |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-187 | El lote vivo | P1 | L | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-169 | Mi finca con varios lotes y zonas | P0 | M | en curso | Entrega 2: Mi finca con el mapa; faltan la capa de la NASA (HU-211); los cultivos en curso ya se ven (HU-165) |
| [EP-16](epicas/EP-16-cuentas-lotes.md) | HU-211 | Capa satelital de la NASA en el mapa del lote | P0 | M | pendiente | Nueva |
| [EP-17](epicas/EP-17-inicio-ambiente.md) | HU-173 | Pantalla de inicio | P0 | M | en curso | Sin 3D; recorrido con la mascota guía y la Tierra girando |
| [EP-17](epicas/EP-17-inicio-ambiente.md) | HU-171 | Diseño de la mascota satélite | P1 | M | en curso | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-17](epicas/EP-17-inicio-ambiente.md) | HU-172 | Expresiones y animaciones de la mascota | P1 | M | en curso | Reacciones en los formularios y en Mi cuenta hechas; faltan las expresiones de los resultados |
| [EP-17](epicas/EP-17-inicio-ambiente.md) | HU-174 | Día y noche en la escena | P1 | S | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-17](epicas/EP-17-inicio-ambiente.md) | HU-175 | Endpoint de condiciones actuales | P1 | S | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-17](epicas/EP-17-inicio-ambiente.md) | HU-176 | Lluvia, nubes y viento en la escena | P1 | M | pendiente | Pasó a P1 el 11 de octubre de 2026: recorte del MVP |
| [EP-18](epicas/EP-18-suelo.md) | HU-181 | Suelo de la región publicado | P0 | M | pendiente | |
| [EP-18](epicas/EP-18-suelo.md) | HU-182 | Suelo de un lote | P0 | M | pendiente | |
| [EP-18](epicas/EP-18-suelo.md) | HU-183 | Señal de suelo en el diagnóstico | P0 | S | pendiente | |
| [EP-18](epicas/EP-18-suelo.md) | HU-184 | Suelo en las estrategias de rotación | P0 | M | pendiente | |
| [EP-18](epicas/EP-18-suelo.md) | HU-212 | Salud del suelo de cada estrategia | P0 | L | pendiente | Cinco criterios con la erosión (decisión 14) |
| [EP-18](epicas/EP-18-suelo.md) | HU-224 | Erosión en la salud del suelo | P0 | S | pendiente | Nueva (8 nov, decisión 14) |
| [EP-18](epicas/EP-18-suelo.md) | HU-185 | Ver el suelo en la web | P0 | S | pendiente | |
