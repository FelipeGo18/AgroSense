# Specs de AgroSense

Aquí vive **qué** se construye y **por qué**. El código implementa lo que dice esta carpeta; si el código y la spec discrepan, se corrige la spec primero y se acuerda.

| Archivo | Contenido |
|---|---|
| `00-vision.md` | Reto, problema, idea, impacto, alcance P0/P1 |
| `01-reglas.md` | Reglas de diseño R1–R10, semáforo, valores permitidos |
| `02-contratos.md` | Tablas Parquet, endpoints, errores, JSON de ejemplo |
| `03-sistemas.md` | Sistemas y subsistemas (D, AG, M, W, S) y sus límites |
| `04-stack.md` | Tecnologías elegidas, por qué y alternativas descartadas |
| `BACKLOG.md` | Índice de todas las HUs con prioridad, tamaño y estado |
| `epicas/` | Una épica por archivo, con sus historias de usuario |
| `_plantilla-epica.md`, `_plantilla-hu.md` | Plantillas para escribir nuevas épicas y HUs |

## Flujo para trabajar una HU

1. Elige una HU `pendiente` de `BACKLOG.md` cuyas dependencias estén resueltas (`docs/orden-de-desarrollo.md`).
2. Léela con su épica y las reglas que aplican.
3. Pásala a `en curso` en el archivo de su épica.
4. Implementa y prueba. Cada criterio de aceptación se marca cuando se cumple.
5. Pásala a `en revisión`; `calidad` la revisa contra R1–R10.
6. Al aprobarse, queda `hecha` en la épica y en `BACKLOG.md`.

## Cómo crear o cambiar una HU

Usa el agente `especificador`. Respeta las plantillas, mantén el contrato y no inventes datos ni fuentes: lo que no se pudo confirmar queda como supuesto.
