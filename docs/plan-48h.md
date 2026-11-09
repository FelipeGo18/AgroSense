# Capacidad y plan de 48 horas

## Capacidad del equipo

Cifras recalculadas el 11 de octubre de 2026 con `specs/BACKLOG.md`, después del recorte del MVP (decisión 12). Son la suma de los tamaños del repositorio (S ≈ 2 h, M ≈ 4 h, L ≈ 8 h), no una medición. **Hay que recalcularlas con el equipo real.**

| | Antes del recorte | Después (MVP) |
|---|---|---|
| HU en total | 116 | 132 (16 nuevas: HU-205 a HU-220) |
| HU P0 | 99 (37 S, 51 M, 11 L) | 92 (35 S, 47 M, 10 L) |
| HU P1 | 17 | 40 |
| Horas-persona del P0 | ≈ 366 | ≈ 338 |

Qué movió las horas:

- Salieron del P0 23 HU (5 S, 14 M y 4 L: ≈ 98 h) y se redujeron HU-093 (de M a S) y HU-169 (de L a M): ≈ 104 h menos.
- Entraron 16 HU nuevas (2 S, 11 M y 3 L: ≈ 72 h) y HU-102 pasó de M a L: ≈ 76 h más. Casi todas son datos de la NASA, estrategias y «Qué cambió».
- El P0 bajó poco en horas, pero cambió de contenido: ahora casi todo sirve al flujo que pide el reto, y más de la mitad de lo nuevo son datos que se pueden adelantar en la fase 0.

### Cuánto queda frente a las horas del equipo

Un equipo de 6 personas rinde unas **168 horas útiles** en el evento (unas 28 por persona, con descanso, comidas y reuniones). Con un 15 % de integración y coordinación, eso alcanza para unas **146 horas** de HU.

| Escenario (depende de HU-004) | Qué llega hecho | P0 que queda para el evento | Con 15 % de integración | Frente a 168 h |
|---|---|---|---|---|
| Hoy | HU-151 a HU-153 (14 h, hechas) | ≈ 324 h | ≈ 373 h | Faltan ≈ 205 h |
| Solo se puede llevar lo que no es código | Además: EP-00 (10 h), el catálogo de EP-06 (18 h) y las etapas de HU-142 (2 h) | ≈ 294 h | ≈ 338 h | Faltan ≈ 170 h |
| Se puede llevar código y datos preparados | Además: el pipeline de datos (EP-03, las 11 HU P0 de EP-04, HU-143 y HU-181: ≈ 66 h), los contratos y las respuestas simuladas (EP-01: 10 h) y el modo 2D base (HU-158: 4 h) | ≈ 214 h | ≈ 246 h | Faltan ≈ 78 h |

**El P0 no cabe en el evento en ningún escenario sin adelantar más o recortar.** Para que quepa hay que llegar con unas 192 horas de HU ya hechas (338 menos 146). Con código permitido, eso es el pipeline, los contratos y unas 68 horas más del motor puro (calificación, aptitud, balance hídrico, señales, estrategias) y de las pantallas en 2D, que se pueden construir contra datos de ejemplo. Si no se permite código, el orden de recorte se aplica desde el inicio. **Qué se adelanta y qué se recorta se decide con el equipo.**

Por eso **HU-004 es urgente: se resuelve esta semana (antes del 17 de octubre).** Define todo el plan.

| Equipo | Horas útiles | ¿Cabe el P0 sin preparar nada antes? |
|---|---|---|
| 4 personas | ≈ 112 h | No |
| 5 personas | ≈ 140 h | No |
| 6 personas | ≈ 168 h | No |

## Fase 0 (10 de octubre al 13 de noviembre)

En este orden (detalle en `docs/orden-de-desarrollo.md`):

1. **Esta semana:** HU-004 (qué se puede llevar preparado) y confirmar la sede (HU-002).
2. **Fichas de los 7 cultivos y reglas de rotación con fuente** (HU-061, HU-199, HU-062, HU-063, HU-142, HU-198). Sin código. Es lo más prioritario: sin fichas, casi todo queda en «datos insuficientes».
3. Cuenta de NASA Earthdata y descargas de prueba de cada producto para un municipio (parte de HU-205 a HU-210): mide el tamaño y confirma el acceso.
4. Diseño en Figma de las pantallas del MVP (`specs/05-frontend.md`, «Pantallas por diseñar del MVP»).
5. El 28 de octubre: enunciado completo (HU-002). Lo que recomiende entra por el mismo mecanismo de adaptadores.
6. Si HU-004 lo permite: pipeline de datos, contratos, motor puro y pantallas 2D contra datos de ejemplo.

## Plan de las 48 horas

Supone que los datos y el catálogo llegan preparados. Si no, el bloque de las horas 3 a 16 se alarga y el orden de recorte se aplica desde el inicio.

| Bloque | Qué pasa | Hito de salida |
|---|---|---|
| Hora 0–3 | Repositorio, contratos en código (HU-012), respuestas simuladas (HU-013), despliegue del esqueleto (HU-023), PostgreSQL en Docker Compose con migraciones (HU-161) y logs (HU-177) | URL pública responde la versión |
| Hora 3–16 | En paralelo. **Datos de la NASA:** POWER ampliado y ET0 (HU-041, HU-042, HU-205, HU-143), NASADEM (HU-206, HU-044), IMERG (HU-207), heladas y calor por mes (HU-045), clima de dos periodos (HU-216), NDVI por municipio (HU-208), suelo (HU-181) y oferta (EP-03). **Motor,** contra Parquet de ejemplo: etapas por calendario y balance hídrico (HU-220, HU-144); aptitud, calificación y señales (HU-191, HU-196, HU-071, HU-077, HU-190, HU-183, HU-072, HU-073); orden de ventanas y semáforo (HU-192, HU-074, HU-076); y **las estrategias de rotación** (HU-081, HU-213, HU-082, HU-212, HU-184, HU-083, HU-084). **Web,** contra respuestas simuladas: inicio (HU-173), entrada y estrategias (HU-214, HU-101, HU-102) y el resultado que reusa el ciclo (HU-092, HU-194, HU-202, HU-203). Autenticación y consentimiento (HU-162, HU-163). Casos de referencia (HU-121) | Cada parte funciona sola |
| Hora 16–20 | Primera integración con datos reales | **Hito 1:** una estrategia de rotación real, con datos de la NASA y el diagnóstico de sus ciclos, visible en la URL pública |
| Hora 20–26 | Descanso por turnos; siempre hay alguien con el despliegue | — |
| Hora 26–34 | Ciclo de una estrategia con el agua del plan (HU-215, HU-146, HU-078, HU-093); «Qué cambió» (HU-217, HU-218, HU-219); lotes con polígono, temporadas, Mi finca y borrar la cuenta (HU-164, HU-165, HU-168, HU-169, HU-166); suelo del lote (HU-182, HU-185); y lo recortable de la NASA, en este orden: NDVI por lote (HU-209), capa GIBS (HU-211) y SMAP (HU-210). Estados, celular y calidad (HU-094, HU-096, EP-12) | **Hito 2:** todo el P0 pasa las pruebas; se congela el alcance |
| Hora 34–42 | P1 solo si el hito 2 se cumplió; si no, pulido y corrección de errores. Ensayo de la demo (HU-131) | Demo ensayada |
| Hora 42–46 | Video, descripción del proyecto y entrega (EP-13); solo correcciones | Entrega enviada |
| Hora 46–48 | Margen ante imprevistos | — |

## Orden de recorte si no alcanza

Se aplica en la hora 34 si hay retraso, o desde el inicio si HU-004 no permite llevar código:

1. Todo el P1
2. Capa GIBS en el mapa del lote (HU-211): queda OpenStreetMap
3. NDVI por lote (HU-209): queda el NDVI por municipio (HU-208)
4. SMAP (HU-210): queda la humedad del suelo de POWER. Va después de lo anterior porque el reto lo nombra primero entre los datos sugeridos (decisión 14)
5. Suelo por lote (HU-182 y su parte de HU-185): queda el suelo del municipio (HU-183)
6. Plan de agua solo con año normal, sin año seco
7. Explicaciones reducidas a una razón por estrategia
8. Pruebas en CI: se ejecutan a mano
9. Último recurso: las cuentas (EP-16, ≈ 40 h sin la capa GIBS). La demo queda en modo sin cuenta, que funciona completo con municipio, área y cultivo anterior

Los pasos 2 a 5 liberan unas 16 horas; no bastan solos. Lo que de verdad hace caber el P0 es lo que se adelanta en la fase 0.

## Lo que nunca se recorta

- Estados «datos insuficientes», «no evaluable» y «no aplica»
- El suelo de la zona y las heladas en el diagnóstico y las rotaciones: es lo que pide el reto
- Al menos un producto de observación satelital de la NASA en el núcleo. POWER, NASADEM e IMERG no se recortan
- Casos de referencia del motor
- Si hay cuentas: consentimiento y borrado de la cuenta (R9)
- Despliegue y video de respaldo
- Citas de fuentes en la entrega

## Roles

| Rol | Épicas | Con 5 o 6 personas |
|---|---|---|
| Datos | EP-03 (HU-031, HU-032), EP-04 (HU-041, HU-042, HU-044, HU-045, HU-205 a HU-210 y HU-216), HU-143, HU-181, HU-122, HU-123; en P1, EP-05, HU-193 y HU-201 | Los datos de la NASA son ≈ 50 h: conviene una segunda persona de apoyo |
| Motor y API | HU-012, HU-144 y HU-220 (antes del diagnóstico), EP-07 (con HU-217 y HU-218), EP-08 (con HU-213), HU-212, HU-146, HU-182 a HU-184, backend de EP-16 (HU-161 a HU-166) | Con 4 personas también se encarga de EP-02 |
| Web | HU-013, EP-09 (con HU-219), EP-10 (HU-214, HU-101, HU-102, HU-215), HU-158, HU-173, web de EP-16 (HU-168, HU-169, HU-211), HU-185 | Una sexta persona se suma aquí |
| Producto y agro | EP-00, EP-06 (fichas de los 7 cultivos y reglas, en la fase 0), HU-142, EP-13 | — |
| Calidad | EP-12: HU-121 (casos de referencia) y revisión cruzada; HU-122 y HU-123 con Datos | Quién lo asume se decide con el equipo |
| Plataforma e integración | EP-02, integración del hito 1, apoyo a Datos | Quinta persona |
