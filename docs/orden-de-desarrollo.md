# Orden de desarrollo de las épicas

El orden lo marcan las dependencias: primero lo que desbloquea a los demás, luego lo que puede avanzar en paralelo y al final lo que integra.

Las etapas de este documento ordenan el trabajo. No confundir con la **fase 0**, que es el periodo previo al evento (ver `docs/glosario.md`).

Reordenado el 11 de octubre de 2026 con el MVP (decisión 12). El flujo que se construye es: lote (o municipio y área) → estrategias de rotación de 3 ciclos → un ciclo con su diagnóstico → agua del plan → qué cambió.

## Etapa 0: cimientos (fase 0 y hora 0, nadie avanza sin esto)

| Orden | Qué | Por qué va primero |
|---|---|---|
| 1 | **HU-004, esta semana** (antes del 17 de octubre) | Confirma si se puede llevar código preparado. Define todo el plan (`docs/plan-48h.md`). |
| 2 | **Fichas de los 7 cultivos y reglas de rotación con fuente** (EP-06: HU-061, HU-199, HU-062, HU-063, HU-198; y HU-142) | **Prioridad alta de la fase 0, sin código.** Papa, arveja, haba, maíz, cebolla de bulbo, zanahoria y avena con vicia. Sin fichas con fuente, la aptitud, el calor, las curvas, el agua y las estrategias quedan en «datos insuficientes». |
| 3 | EP-00 Alcance piloto (HU-001, HU-002, HU-003) | Región, sede y datos. El 28 de octubre sale el enunciado completo: lo que recomiende entra por adaptadores. |
| 4 | Acceso a los datos de la NASA: cuenta de Earthdata y una descarga de prueba de cada producto (parte de HU-205 a HU-210) | Mide el tamaño de IMERG y MODIS y confirma el acceso antes de depender de ellos. |
| 5 | EP-01 Contratos y datos de ejemplo | Congela el esquema de datos y el OpenAPI y deja datos y respuestas de ejemplo. Habilita el paralelismo. Incluye las tablas nuevas de la NASA, `/rotations` con estrategias y `/changes`. |
| 6 | EP-02 Base desplegada | Repositorio, CI y un despliegue vacío que ya funcione. Así se integra desde el principio. |

En paralelo, durante la fase 0, se diseñan en Figma las pantallas del MVP (`specs/05-frontend.md`, «Pantallas por diseñar del MVP»): se diseña antes de programar. El kit y los tokens (HU-151 a HU-153) ya están hechos.

## Etapa 1: en paralelo, cada quien sobre el contrato

| Frente | Épicas | Trabaja con |
|---|---|---|
| Datos de la NASA | EP-04: POWER ampliado (HU-041, HU-042, HU-205), NASADEM y corrección de temperatura (HU-206, HU-044), IMERG (HU-207), heladas y calor por mes (HU-045), clima de dos periodos (HU-216) y NDVI por municipio (HU-208). ET0 por Penman-Monteith (HU-143) | Datos reales producidos por el pipeline |
| Otros datos | Suelo de EP-18 (HU-181) y oferta de EP-03 | Datos reales producidos por el pipeline |
| Motor, primero | Etapas por calendario (HU-220) y balance hídrico con la textura del suelo (HU-144). Van antes del diagnóstico: la señal `water` necesita el balance y la duración de la ventana sale de las etapas | Parquet de ejemplo |
| Motor, después | EP-07: aptitud (HU-191), calificación (HU-196), las seis señales (HU-071, HU-077, HU-190, HU-183, HU-072, HU-073), orden de las ventanas (HU-192), semáforo con dos luces (HU-074) y endpoint (HU-076) | Parquet de ejemplo |
| Motor, el centro | EP-08: filtro (HU-081), ciclos con su diagnóstico (HU-213), orden (HU-082), salud del suelo (HU-212, con HU-184), explicación (HU-083) y endpoint (HU-084) | Parquet de ejemplo |
| Web | Inicio (HU-173), entrada y estrategias (HU-214, HU-101, HU-102) y el resultado del diagnóstico que reusa cada ciclo (EP-09: HU-091, HU-092, HU-194, HU-202, HU-203), en 2D (HU-158) | Respuestas simuladas (MSW) |
| Cuentas | Base de datos y autenticación (HU-161 a HU-163) | PostgreSQL en Docker |
| Calidad | EP-12 (HU-121 casos de referencia) | Resultado esperado escrito antes de programar |

Al terminar esta etapa las estrategias deben funcionar de punta a punta, aunque sea con datos de ejemplo. **Hito 1** (horas 16–20): una estrategia de rotación real, con datos de la NASA y el diagnóstico de sus ciclos, visible en la URL pública.

## Etapa 2: integrar y extender

| Orden | Épica | Nota |
|---|---|---|
| 7 | Cambio de datos de ejemplo a reales | Paso de integración; si el contrato se respetó, encaja. |
| 8 | Ciclo de una estrategia con el agua del plan (HU-215, HU-146, HU-078, HU-093) | Necesita el endpoint de estrategias y el balance hídrico. |
| 9 | «Qué cambió» (HU-217, HU-218, HU-219) | Necesita el clima de dos periodos (HU-216) y el orden de ventanas (HU-192). |
| 10 | EP-16 Cuentas y lotes: lotes con polígono, temporadas, Mi finca con una zona y borrar la cuenta (HU-164 a HU-166, HU-168, HU-169); después, el suelo del lote (HU-182) y su vista (HU-185) | Desde el lote se entra a las estrategias. |
| 11 | Lo recortable de la NASA, en este orden: SMAP (HU-210) y capa GIBS (HU-211). El NDVI por lote (HU-209) pasó a P1 (decisión 15) | Si falta tiempo, se recorta al revés: primero GIBS y al final SMAP, que el reto nombra primero (decisión 14). |
| 12 | EP-12 Calidad y trazabilidad | Transversal: empieza pequeño en la etapa 1 y se cierra aquí. |

## Etapa 3: cierre

| Orden | Épica | Nota |
|---|---|---|
| 13 | EP-13 Demo y entrega | Guion que abre con rotación, suelo, NASA y qué cambió, y deja la oferta al final. Caso ensayado, video y documentación de fuentes. Reservar tiempo real para ensayar. |

## Fuera del camino crítico (P1)

- Todo lo que pasó a P1 el 11 de octubre de 2026: la escena 3D, el descenso, el motion y el prototipo (HU-154 a HU-156, HU-159), la mascota animada (HU-171, HU-172), el clima en vivo (HU-174 a HU-176), el lote vivo (HU-187), el calendario, la línea de tiempo, las semanas y la etapa por temperatura (HU-179, HU-180, HU-186, HU-193, HU-150), la finca temporal (HU-141, HU-145), los cultivos alternativos (HU-197), el perfil (HU-160), el progreso (HU-167), la trazabilidad (HU-178), restaurar lo borrado (HU-204) y el modo simulación (HU-014).
- **EP-05 Mercado SIPSA** y **EP-11 Escenarios**, solo si sobra tiempo.
- Las fuentes de contraste de la oferta (HU-201) y las siembras registradas en AgroSense (HU-200).
- Las tres señales del P1 (`excess_rain`, `disease` y `harvest_weather`, HU-195) con sus datos (HU-046). Mientras no existan, no aparecen en la respuesta.
- EP-05 tiene un riesgo extra: no está verificado que SIPSA cubra lo necesario. El diagnóstico debe funcionar sin ella, con la señal de mercado como «datos insuficientes».

## Reglas para no atascarse

1. El camino crítico es HU-004 → fichas de los 7 cultivos → EP-01 → datos de la NASA → etapas y balance hídrico → diagnóstico → estrategias de rotación integradas → demo. Todo lo demás se recorta antes.
2. Orden de recorte si no alcanza: ver `docs/plan-48h.md`.
3. No empezar ninguna épica de la etapa 1 hasta que Haider o Felipe den por congelado el contrato de EP-01.
4. Ninguna pantalla nueva se programa sin su diseño aprobado en Figma.
