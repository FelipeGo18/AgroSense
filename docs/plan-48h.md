# Capacidad y plan de 48 horas

## Capacidad del equipo

El punto más crítico de viabilidad es la capacidad. El P0 que se hace durante el evento suma unas **170 horas-persona**: 116 del núcleo (diagnóstico, rotaciones, plan de agua, calidad y entrega), 38 de cuentas (EP-16, con autenticación propia) y 16 del inicio y el paisaje vivo (EP-17, sin HU-171, que es diseño de la fase 0). Con un 15 % de integración y coordinación son cerca de **196 horas**. Con descanso, comidas y reuniones, cada persona rinde unas **28 horas útiles**.

| Equipo | Horas útiles | ¿Cabe el P0 sin preparar nada antes? |
|---|---|---|
| 4 personas | ≈ 112 h | No |
| 5 personas | ≈ 140 h | No |
| 6 personas | ≈ 168 h | No |

Space Apps permite equipos de hasta 6 personas. Lo que hace caber el P0 es lo que se prepara en la fase 0, y eso depende de HU-004:

- **Si los términos permiten llevar código preparado:** llegan hechos el frontend base de EP-15 (escena, componentes, modo simulación) y, si se adelantan, los datos (EP-03, EP-04 y HU-143, unas 20 horas). Con 6 personas cabe con poco margen; con 5, solo con el orden de recorte.
- **Si no lo permiten:** se llevan diseños, guías y assets; en el evento se construye primero la versión 2D (modo ligero) y la escena 3D solo si sobra tiempo, porque el 3D es una mejora (`specs/05-frontend.md`). El orden de recorte se aplica desde el inicio.

**Las estimaciones son gruesas: hay que recalcularlas con el equipo real.**

## Plan de las 48 horas

| Bloque | Qué pasa | Hito de salida |
|---|---|---|
| Hora 0–3 | Repositorio, contratos en código (HU-012), respuestas simuladas (HU-013), despliegue del esqueleto (HU-023) y PostgreSQL en Docker Compose con migraciones (HU-161) | URL pública responde la versión |
| Hora 3–16 | En paralelo: datos (EP-03, EP-04), motor contra Parquet de ejemplo (EP-07), web contra respuestas simuladas (EP-09 e inicio, HU-173), autenticación y consentimiento (HU-162, HU-163) y casos de referencia (HU-121) | Cada parte funciona sola |
| Hora 16–20 | Primera integración con datos reales | **Hito 1:** un diagnóstico real visible en la URL pública |
| Hora 20–26 | Descanso por turnos; siempre hay alguien con el despliegue | — |
| Hora 26–34 | Rotaciones (EP-08, EP-10), plan de agua (EP-14), lotes, temporadas y Mi finca (HU-164 a HU-169), paisaje vivo (HU-174 a HU-176), estados y trazabilidad (EP-12) | **Hito 2:** todo el P0 pasa las pruebas; se congela el alcance |
| Hora 34–42 | P1 solo si el hito 2 se cumplió; si no, pulido y corrección de errores. Ensayo de la demo | Demo ensayada |
| Hora 42–46 | Video, descripción del proyecto y entrega (EP-13); solo correcciones | Entrega enviada |
| Hora 46–48 | Margen ante imprevistos | — |

## Orden de recorte si hay retraso en la hora 34

1. Todo el P1
2. Lluvia, nubes y viento en la escena (HU-175, HU-176): queda solo día y noche
3. Progreso del lote (HU-167)
4. Reducir HU-093 a una sola gráfica
5. Plan de agua solo con año normal, sin año seco
6. Explicaciones reducidas a una razón por opción
7. Pruebas en CI: se ejecutan a mano
8. Último recurso: las cuentas (EP-16). La demo queda en modo sin cuenta, que funciona completo

## Lo que nunca se recorta

- Estados «datos insuficientes» y «no evaluable»
- Casos de referencia del motor
- Si hay cuentas: consentimiento y borrado de la cuenta (R9)
- Despliegue y video de respaldo
- Citas de fuentes en la entrega

## Roles

| Rol | Épicas | Con 5 o 6 personas |
|---|---|---|
| Datos | EP-03, EP-04, EP-05, HU-143, HU-122, HU-123 | — |
| Motor y API | HU-012, EP-07, EP-08, HU-144, HU-146, backend de EP-16 (HU-161 a HU-167), HU-175, motor de EP-11 | Con 4 personas también se encarga de EP-02 |
| Web | HU-013, HU-014, EP-09, EP-10, EP-15 (fase 0), EP-17 (salvo HU-175), web de EP-16 (HU-168, HU-169), HU-141, HU-145, interfaz de EP-11 | Una sexta persona se suma aquí |
| Producto y agro | EP-00, EP-06, HU-142, HU-121, EP-13 | — |
| Plataforma e integración | EP-02, integración del hito 1, apoyo a Datos | Quinta persona |
