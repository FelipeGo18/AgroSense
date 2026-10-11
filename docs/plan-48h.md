# Capacidad y plan de 48 horas

## Capacidad del equipo

El punto más crítico de viabilidad es la capacidad. Según `specs/BACKLOG.md` (11 de octubre de 2026), el P0 son **99 HU** (37 S, 51 M y 11 L): unas **366 horas-persona** con los tamaños del repositorio (S ≈ 2 h, M ≈ 4 h, L ≈ 8 h). El 10 de octubre eran unas 302; subió por las ventanas de siembra, las prioridades, el método FAO, las varias fuentes y los lotes divisibles (decisiones 9 a 11). Sin lo que se hace en la fase 0 (EP-00, EP-06, EP-15, HU-142 y HU-171: 80 horas), el P0 del evento suma unas **286 horas-persona**; con un 15 % de integración y coordinación son cerca de **329 horas**. Con descanso, comidas y reuniones, cada persona rinde unas **28 horas útiles**. El P0 no cabe en el evento sin adelantar más en la fase 0 o recortar: **qué se recorta se decide con el equipo.**

| Equipo | Horas útiles | ¿Cabe el P0 sin preparar nada antes? |
|---|---|---|
| 4 personas | ≈ 112 h | No |
| 5 personas | ≈ 140 h | No |
| 6 personas | ≈ 168 h | No |

Space Apps permite equipos de hasta 6 personas. Lo que hace caber el P0 es lo que se prepara en la fase 0, y eso depende de HU-004:

- **Si los términos permiten llevar código preparado:** llegan hechos el frontend base de EP-15 (escena, componentes, modo simulación) y, si se adelantan, los datos (EP-03, EP-04, HU-143 y HU-181, unas 34 horas). Aun así quedan unas 295 horas con integración, más de las 168 de 6 personas: **hay que adelantar más en la fase 0 o recortar. El recorte se decide con el equipo.**
- **Si no lo permiten:** se llevan diseños, guías y assets; en el evento se construye primero la versión 2D (modo ligero) y la escena 3D solo si sobra tiempo, porque el 3D es una mejora (`specs/05-frontend.md`). El orden de recorte se aplica desde el inicio.

**Las estimaciones son gruesas: hay que recalcularlas con el equipo real.**

> Cifras recalculadas el 11 de octubre de 2026 con `specs/BACKLOG.md`, después del cambio a ventanas de siembra (decisión 9, HU-190 a HU-195) y a prioridades, método FAO, varias fuentes y lotes divisibles (decisiones 10 y 11, HU-196 a HU-204; HU-074, HU-121 y HU-165 pasaron de M a L). Son la suma de los tamaños, no una medición.

## Plan de las 48 horas

| Bloque | Qué pasa | Hito de salida |
|---|---|---|
| Hora 0–3 | Repositorio, contratos en código (HU-012), respuestas simuladas (HU-013), despliegue del esqueleto (HU-023) y PostgreSQL en Docker Compose con migraciones (HU-161) | URL pública responde la versión |
| Hora 3–16 | En paralelo: datos (EP-03, EP-04 con HU-042, HU-044, HU-045 y HU-193, lluvia y ET0 mensuales HU-143, suelo HU-181); motor contra Parquet de ejemplo, en este orden: primero el balance hídrico con la textura del suelo y las etapas de una ventana (HU-144, HU-150, HU-186), porque la señal `water` los necesita, y después EP-07 (aptitud HU-191, calificación HU-196, agua HU-071, heladas HU-077, calor HU-190, suelo HU-183, oferta, mercado, orden de ventanas HU-192, semáforo con prioridades y dos luces HU-074, alternativas HU-197, HU-078) y el endpoint del calendario (HU-179); web contra respuestas simuladas (EP-09 con HU-194, HU-202 y HU-203, e inicio, HU-173), autenticación y consentimiento versión 3 (HU-162, HU-163), logs (HU-177) y casos de referencia (HU-121) | Cada parte funciona sola |
| Hora 16–20 | Primera integración con datos reales | **Hito 1:** un diagnóstico real visible en la URL pública |
| Hora 20–26 | Descanso por turnos; siempre hay alguien con el despliegue | — |
| Hora 26–34 | Rotaciones con suelo (EP-08, HU-184, EP-10), finca, plan de agua y vista del calendario (lo que queda de EP-14: HU-141, HU-145, HU-146, HU-180), lotes, temporadas con partes que se dividen y se juntan, historial con «Restaurar», perfil, trazabilidad y Mi finca (HU-160, HU-164 a HU-169, HU-178, HU-204), suelo del lote (HU-182, HU-185), paisaje vivo (HU-174 a HU-176), estados y calidad (EP-12) | **Hito 2:** todo el P0 pasa las pruebas; se congela el alcance |
| Hora 34–42 | P1 solo si el hito 2 se cumplió; si no, pulido y corrección de errores. Ensayo de la demo | Demo ensayada |
| Hora 42–46 | Video, descripción del proyecto y entrega (EP-13); solo correcciones | Entrega enviada |
| Hora 46–48 | Margen ante imprevistos | — |

## Orden de recorte si hay retraso en la hora 34

1. Todo el P1
2. Lluvia, nubes y viento en la escena (HU-175, HU-176): queda solo día y noche
3. Progreso del lote (HU-167)
4. Suelo por lote (HU-182 y su parte de HU-185): queda el suelo del municipio (HU-183)
5. Vista del calendario (HU-180): las señales de heladas y de calor y las mejores ventanas siguen en el diagnóstico
6. Reducir HU-093 a una sola gráfica
7. Plan de agua solo con año normal, sin año seco
8. Explicaciones reducidas a una razón por opción
9. Pruebas en CI: se ejecutan a mano
10. Último recurso: las cuentas (EP-16). La demo queda en modo sin cuenta, que funciona completo

## Lo que nunca se recorta

- Estados «datos insuficientes», «no evaluable» y «no aplica»
- El suelo de la zona y las heladas en el diagnóstico y las rotaciones: es lo que pide el reto
- Casos de referencia del motor
- Si hay cuentas: consentimiento y borrado de la cuenta (R9)
- Despliegue y video de respaldo
- Citas de fuentes en la entrega

## Roles

| Rol | Épicas | Con 5 o 6 personas |
|---|---|---|
| Datos | EP-03 (HU-031, HU-032; HU-201 en P1), EP-04 (con HU-042, HU-044, HU-045 y HU-193), EP-05, HU-143, HU-181, HU-122, HU-123 | — |
| Motor y API | HU-012, HU-144, HU-150 y HU-186 (antes del diagnóstico), EP-07 (con HU-077, HU-078, HU-190 a HU-192, HU-196 y HU-197; HU-195 en P1), EP-08, HU-146, HU-179, HU-182 a HU-184, backend de EP-16 (HU-160 a HU-167, HU-178, HU-204), HU-175, motor de EP-11; en P1, HU-200 | Con 4 personas también se encarga de EP-02 |
| Web | HU-013, HU-014, EP-09 (con HU-194, HU-202 y HU-203), EP-10, EP-15 (fase 0), EP-17 (salvo HU-175), web de EP-16 (HU-168, HU-169 y la vista de HU-204), HU-141, HU-145, HU-180, HU-185, interfaz de EP-11 | Una sexta persona se suma aquí |
| Producto y agro | EP-00, EP-06 (con HU-063, HU-198 y HU-199, en la fase 0), HU-142, EP-13 | — |
| Calidad | EP-12: HU-121 (casos de referencia) y revisión cruzada; HU-122 y HU-123 con Datos | Quién lo asume se decide con el equipo |
| Plataforma e integración | EP-02, integración del hito 1, apoyo a Datos | Quinta persona |
