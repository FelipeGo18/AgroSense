# Agentes de AgroSense

Un agente por rol del equipo. Cada uno vive en `.claude/agents/<nombre>.md`, con su alcance, las épicas que le corresponden y lo que no debe hacer. Todos comparten las reglas de `CLAUDE.md` y `specs/01-reglas.md`.

## Catálogo

| Agente | Rol | Subsistemas | Épicas y HUs | Úsalo cuando |
|---|---|---|---|---|
| `especificador` | Escribe y mantiene las specs | — | Todas (solo specs) | Hay que crear, afinar o validar épicas y HUs |
| `producto-agro` | Producto y agro | AG1–AG3, S4 | EP-00, EP-06, EP-13, HU-142 | Decidir alcance, fichas de cultivo, reglas de rotación, demo |
| `datos` | Pipeline de datos | D1–D4 | EP-03, EP-04, EP-05, HU-143 | Ingesta, limpieza, indicadores, Parquet |
| `motor-api` | Motor de decisión y API | M1–M9 | HU-012, EP-07, EP-08, HU-144, HU-146, backend de EP-16, HU-175, motor de EP-11 | Semáforo, rotaciones, balance hídrico, cuentas, condiciones actuales, endpoints |
| `web` | Aplicación web | W1–W9, S5 | HU-013, HU-014, EP-09, EP-10, EP-15, EP-17, web de EP-16, HU-141, HU-145, interfaz de EP-11 | Identidad visual, mascota, 3D, animación, pantallas, cuenta, modo simulación, accesibilidad |
| `calidad` | Calidad y trazabilidad | S3 | EP-12 | Casos de referencia, manifiesto, reproducibilidad, revisión |
| `plataforma` | Repositorio, CI y despliegue | S1, S2 | EP-02, integración del hito 1 | Arranque, GitHub Actions, Docker, URL pública |

## Cómo se invoca

- Claude Code elige el agente según su descripción. Para forzarlo: «usa el agente `motor-api` para HU-074».
- Una HU siempre se asigna con su código. El agente debe leer la HU, su épica y las reglas antes de tocar nada.
- Con 4 personas, `plataforma` lo asume `motor-api`. Con 5 o 6, hay una persona dedicada y la sexta refuerza `web`.

## Reglas de convivencia entre agentes

1. **Cada uno edita lo suyo.** Si necesita un cambio en el territorio de otro, lo pide en la spec o en el PR; no lo hace por su cuenta.
2. **El contrato manda.** Haider es el responsable de `specs/02-contratos.md`: ningún agente lo cambia sin su aprobación.
3. **Revisión cruzada.** `calidad` revisa las fichas de cultivo y las reglas (HU-061, HU-062, HU-142) antes de que se den por hechas.
4. **Sin fuente no hay dato.** Cualquier agente que agregue un dato o una regla agrega también su entrada en `sources`.
5. **Lo que falta se declara.** Si algo no se puede confirmar, queda escrito como supuesto en la spec, no se asume.

## Definición de «hecha» para una HU

- Todos los criterios de aceptación cumplidos y marcados en el archivo de la épica.
- Pruebas que cubren los criterios, corriendo en CI (o a mano si se aplicó el recorte).
- No viola ninguna regla R1–R10.
- Si toca el contrato, está actualizado y aprobado por Haider.
- El estado queda actualizado en la épica y en `specs/BACKLOG.md`.
