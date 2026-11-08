# Revisión de un PR

Lo que se revisa antes de aceptar un PR. Quien lo abre lo repasa primero; quien revisa lo usa como lista. La descripción sigue la plantilla de `.github/pull_request_template.md`.

## Resultado de la revisión

- **Veredicto:** se acepta o se piden cambios.
- **Hallazgos**, cada uno con su `archivo:línea`:
  - **Bloquea:** un bug, un hueco de seguridad, una regla R1–R10 violada o un cambio de contrato sin aprobar.
  - **Debe corregirse:** estilo, documentación, una prueba que falta o un dato quemado.
  - **Sugerencia:** opcional.

Antes de aceptar, se baja la rama, se corre y se hace el recorrido de punta a punta: no basta con leer el diff.

## 1. Alcance, rama y commits

- [ ] Una sola funcionalidad, o máximo tres muy relacionadas, y cada una con su HU.
- [ ] El PR va a `desarrollo` (nunca a `produccion`) y está al día con `desarrollo`, sin conflictos.
- [ ] La rama se llama `feature/…`, `fix/…` o `docs/…`.
- [ ] Los commits son `tipo: descripción en español (HU-xxx)`, con `tipo` entre `feat`, `fix`, `docs`, `perf`, `test` y `chore`.
- [ ] Sin firma de Claude ni de otra herramienta (`Co-Authored-By`, «Generated with …») en los commits ni en la descripción.
- [ ] La descripción sigue la plantilla y dice lo que de verdad hace el PR: nada que no esté en el diff ni al revés.

## 2. Código

- [ ] Sigue el estilo del código que ya hay: nombres en inglés y `snake_case` en el backend, textos y comentarios en español, el mismo tipo de módulos, funciones y manejo de errores.
- [ ] Respeta las carpetas: `backend/engine` (motor puro), `backend/api`, `backend/accounts`, `pipeline/sources/<fuente>`, `catalog/`, `web/src/{pages,features,components,api}`. No crea carpetas vacías.
- [ ] No hay código comentado, `print`, `console.log` ni un TODO sin su HU.
- [ ] **Sin datos quemados:** direcciones, puertos, claves, rutas, fechas de corte, umbrales o listas de cultivos no se escriben en el código.
  - Lo que cambia entre equipos o entornos va en el **`.env`**: el de la raíz para la API y el pipeline, y `web/.env` para la web (con el prefijo `VITE_`). Cada quien hace el suyo copiando `.env.example` o `web/.env.example`; el `.env` nunca va a git.
  - El código no lee el `.env` por su cuenta: el backend lo lee en un solo lugar (la clase `Settings`) y la web también (`config.ts`). Una variable nueva se agrega ahí.
  - Lo que es igual para todos y tiene fuente (umbrales, cultivos, reglas, la región) va en los `.yaml` versionados (`backend/config/`, `catalog/`, `pipeline/region.yaml`), no en el `.env`.
- [ ] Cada variable nueva está en `.env.example` (o `web/.env.example`), con un comentario que dice para qué sirve, y su valor por defecto es el seguro para producción.
- [ ] **Modo de desarrollo:** los pasos pesados o externos (descargas grandes, tareas en segundo plano, servicios de terceros) se pueden apagar con una variable del `.env` para trabajar en local, como hoy `AGROSENSE_API_DOCS=true` enciende la documentación de la API. Se documenta en `.env.example` y en el README del módulo, y apagarlo nunca inventa datos: lo que falta queda como `insufficient_data` (R1).

## 3. Reglas del proyecto (R1–R10)

- [ ] R1: sin datos es `insufficient_data` con `level` nulo, nunca un valor de relleno.
- [ ] R5: todo dato ficticio va rotulado como ejemplo, en el archivo y en la interfaz.
- [ ] R6: `backend/engine/` no importa FastAPI ni SQLAlchemy y no abre archivos.
- [ ] R7: se une por `municipality_id`, nunca por nombre.
- [ ] R8: cada dato y cada regla apunta a una entrada de `sources`.
- [ ] R9: los endpoints de cálculo no guardan datos de la finca.
- [ ] R10: el riego y el suelo se dicen como estimación de la zona.
- [ ] **Contrato:** si cambia `specs/02-contratos.md`, un endpoint, un campo o un error, Felipe o Haider lo aprobaron; queda «aprobado por …» con la fecha, y `web/src/api/schema.d.ts` está regenerado (`npm run api:types`).

## 4. Web

- [ ] Usa los estilos de la web: los tokens de color y tipografía, `container-page` y los componentes de `components/ui` (`Button`, `Card`, `TextField`, `Alert`…). Nada de colores ni tamaños sueltos que ya existan como token.
- [ ] La pantalla sale de un diseño en Figma o en `design/`.
- [ ] Textos en español y al agricultor se le trata de usted.
- [ ] Ningún botón ni control sin función.
- [ ] Cumple `web/CLAUDE.md`: modo ligero (`useAnimated()`), diseño adaptable desde 320 px, sin scroll horizontal y objetivos táctiles de 44 px.
- [ ] Cada ruta nueva está en `npm run test:responsive`.
- [ ] Accesible: etiquetas en los campos, encabezados en orden y regiones con nombre.

## 5. Backend, API y logs

- [ ] La API sigue dejando logs como ya lo hace (HU-177, `backend/config/logging.py`):
  - [ ] Se usa `get_logger("agrosense.<módulo>")`, nunca `print` ni `logging` suelto.
  - [ ] Los eventos son nombres en `snake_case` con sus datos como campos (`log.warning("dataset_unavailable", detail=…)`), no frases armadas.
  - [ ] Lo nuevo que puede fallar deja su log: errores de fuentes externas, descargas y tareas en segundo plano (cuándo empieza, cuándo termina y por qué falla).
  - [ ] Ningún log lleva secretos ni datos de la finca. Una llave sensible nueva se agrega a `SECRET_KEYS` (R9).
- [ ] Las migraciones de Alembic tienen `downgrade` y dejan una sola cabeza.
- [ ] Los errores responden con el formato de errores del contrato.

## 6. Seguridad

- [ ] No hay secretos, tokens ni `.env` en el diff.
- [ ] Las entradas se validan con Pydantic, y las consultas pasan por el ORM sin armar SQL con texto.
- [ ] Cada recurso de una cuenta se revisa contra su dueño (authz): un usuario no ve ni cambia lo de otro.
- [ ] Las descargas externas:
  - tienen timeout y límite de tamaño;
  - verifican TLS (nunca `verify=False`);
  - no siguen direcciones que llegan del usuario;
  - si fallan, dejan `insufficient_data` sin tumbar la API.
- [ ] Las tareas en segundo plano no bloquean el arranque de la API y no corren dos veces si hay varios procesos.
- [ ] Los endpoints nuevos que cambian datos exigen sesión y pasan por la protección contra CSRF.

## 7. Dependencias y datos

- [ ] **Versiones exactas en la web:** en `web/package.json`, `"paquete": "1.2.3"`, sin `^` ni `~`. El `package-lock.json` queda al día.
- [ ] En Python, cada dependencia sigue la forma del resto de `pyproject.toml`, y el `uv.lock` (que fija la versión exacta) queda al día.
- [ ] Cada dependencia nueva está justificada en la descripción: qué hace que no haga ya algo del proyecto.
- [ ] No se suben archivos pesados: `data/raw` no va a git, y se revisa el tamaño de lo que entra a `data/published`.
- [ ] El dataset se reconstruye con `uv run python -m pipeline.build`, y `manifest.json` queda actualizado.

## 8. Pruebas

- [ ] Backend, en Docker: `docker compose run --rm app uv run pytest`, `ruff check .` y `ruff format --check .`
- [ ] Web: `npm run typecheck`, `lint`, `format:check`, `test` y `build`.
- [ ] Lo nuevo trae sus propias pruebas, incluidos los casos de error y de «sin datos». No basta con que lo de antes siga en verde.
- [ ] Probado a mano de punta a punta, con la API y la base de verdad.

## 9. Documentación

- [ ] Los criterios de aceptación están marcados en su épica, con el estado de la HU al día.
- [ ] `specs/BACKLOG.md` refleja el cambio.
- [ ] Si cambia una regla o una decisión: `docs/decisiones.md` o `docs/registro-de-decisiones.md`, y `specs/01-reglas.md`.
- [ ] Una fuente nueva está en `docs/fuentes.md` y en `sources`.
- [ ] El README del módulo trae sus comandos y variables nuevas.
