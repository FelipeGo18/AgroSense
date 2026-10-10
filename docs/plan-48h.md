# Capacidad y plan de 48 horas

## Capacidad del equipo

El punto más crítico de viabilidad es la capacidad. Con el plan de agua, el P0 que se hace durante el evento suma unas **116 horas-persona**, más un 15 % de integración y coordinación: cerca de **133 horas**. Con descanso, comidas y reuniones, cada persona rinde unas **28 horas útiles**.

| Equipo | Horas útiles | ¿Cabe el P0? |
|---|---|---|
| 4 personas | ≈ 112 h | No |
| 5 personas | ≈ 140 h | Sí, con poco margen |
| 6 personas | ≈ 168 h | Sí, con margen para el P1 |

Space Apps permite equipos de hasta 6 personas. Si los términos de 2026 permiten preparar antes, mover EP-03, EP-04 y HU-143 a la fase 0 libera unas 20 horas del evento. Con 4 personas eso es necesario y aun así queda justo. **Las estimaciones son gruesas: hay que recalcularlas con el equipo real.**

## Plan de las 48 horas

| Bloque | Qué pasa | Hito de salida |
|---|---|---|
| Hora 0–3 | Repositorio, contratos en código (HU-012), respuestas simuladas (HU-013) y despliegue del esqueleto (HU-023) | URL pública responde la versión |
| Hora 3–16 | En paralelo: datos (EP-03, EP-04), motor contra Parquet de ejemplo (EP-07), web contra respuestas simuladas (EP-09) y casos de referencia (HU-121) | Cada parte funciona sola |
| Hora 16–20 | Primera integración con datos reales | **Hito 1:** un diagnóstico real visible en la URL pública |
| Hora 20–26 | Descanso por turnos; siempre hay alguien con el despliegue | — |
| Hora 26–34 | Rotaciones (EP-08, EP-10), plan de agua (EP-14), estados y trazabilidad (EP-12) | **Hito 2:** todo el P0 pasa las pruebas; se congela el alcance |
| Hora 34–42 | P1 solo si el hito 2 se cumplió; si no, pulido y corrección de errores. Ensayo de la demo | Demo ensayada |
| Hora 42–46 | Video, descripción del proyecto y entrega (EP-13); solo correcciones | Entrega enviada |
| Hora 46–48 | Margen ante imprevistos | — |

## Orden de recorte si hay retraso en la hora 34

1. Todo el P1
2. Reducir HU-093 a una sola gráfica
3. Plan de agua solo con año normal, sin año seco
4. Explicaciones reducidas a una razón por opción
5. Pruebas en CI: se ejecutan a mano

## Lo que nunca se recorta

- Estados «datos insuficientes» y «no evaluable»
- Casos de referencia del motor
- Despliegue y video de respaldo
- Citas de fuentes en la entrega

## Roles

| Rol | Épicas | Con 5 o 6 personas |
|---|---|---|
| Datos | EP-03, EP-04, EP-05, HU-143, HU-122, HU-123 | — |
| Motor y API | HU-012, EP-07, EP-08, HU-144, HU-146, motor de EP-11 | Con 4 personas también se encarga de EP-02 |
| Web | HU-013, EP-09, EP-10, HU-141, HU-145, interfaz de EP-11 | Una sexta persona se suma aquí |
| Producto y agro | EP-00, EP-06, HU-142, HU-121, EP-13 | — |
| Plataforma e integración | EP-02, integración del hito 1, apoyo a Datos | Quinta persona |
