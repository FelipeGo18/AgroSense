# Verificación de HU-233

Revisión del 15 de noviembre de 2026 sobre la base `24059e6`, con las correcciones de esta revisión en el árbol de trabajo. Los cambios no se han confirmado ni subido desde esta ejecución.

## Web en Docker

- TypeScript y lint: pasan.
- Vitest: 413 pruebas pasan en 36 archivos, con dos workers.
- Build y prerender: pasan.
- Regresiones: verdor de la zona en el texto accesible; coincidencia del mensaje de fecha con el backend; textos fuera de JSX, incluidos los casos de `LAYER_NAME`, `STATUS_TEXT` y plantillas; imports de navegación que conservan el idioma; pie de página del lote.

## Responsive en inglés

Resultado final: **880/880** comprobaciones aprobadas en inglés, con `SESSION` y `LOT`. La matriz completa tiene 40 rutas y estados, 11 tamaños y dos modos de movimiento. Se utilizó una cuenta temporal en PostgreSQL aislado, sin usar la base de la nube. Las peticiones de cuenta y finca usan la API real; los estados de cálculo se fuerzan con `VITE_SIMULATION=true`.

Las rutas se distribuyen en cuatro lotes disjuntos de diez rutas para ejecutar el mismo script sin omitir tamaños, estados ni modos. El segundo lote se repitió tras atascarse Chrome; se verificó que el script no había cambiado antes de combinarlo con los otros tres. No se cuentan las pasadas interrumpidas para corregir defectos.

La primera pasada con sesión detectó ausencia del pie de página en las vistas con mapa y el ancho táctil insuficiente de «Edit» en Mi cuenta. Ambos se corrigieron; las comprobaciones rápidas de cuenta, finca, lote y edición pasan a 320 y 1024 px con el suelo desplegado.

Script revisado: SHA-256 `db85523c38bb62c8bc86798d94aa1221de5114eca4949176541dcb6b60a58c7e`.

## Recorrido automatizado con API y base reales

Sin simulación, contra una API temporal y PostgreSQL local aislado:

| Flujo | Resultado | Idioma |
| --- | --- | --- |
| Diagnóstico | HTTP 200, dataset `2026.11.26` | inglés |
| Estrategias | HTTP 200, 10 estrategias, dataset `2026.11.26` | inglés |
| Mi finca | HTTP 200 | inglés |
| Detalle del lote | HTTP 200, dataset `2026.11.26` | inglés |

Se conservaron las razones originales de la API y su aviso de idioma. Esta ejecución automatizada y sus capturas no se marcan como revisión manual del autor.

## Verificación manual y cierre

- [x] El autor recorre en inglés la consulta, las estrategias y sus ciclos, y Mi finca con la simulación desactivada y la API y la base reales.

El autor confirmó el 15 de noviembre de 2026 que completó este recorrido y que funciona correctamente con los datos de la API real. Con esta confirmación, la HU queda **hecha** en la épica, el backlog y el PR.
