<!--
Antes de pedir revisión, revise su PR con docs/revision-de-pr.md.
El PR va a `desarrollo`, nunca a `produccion`. Sin firma de Claude ni de otra herramienta en los commits ni aquí.
Borre las secciones que no apliquen y estos comentarios.
-->

## Qué hace

<!-- Una o dos frases: qué puede hacer el usuario ahora que antes no podía. Solo lo que de verdad hace este PR. -->

## Historias de usuario

<!-- Una funcionalidad, o máximo tres muy relacionadas. -->

- HU-xxx: título (EP-xx) · criterios marcados en la épica: sí / no

## Cambios

- Backend:
- Web:
- Pipeline y datos:
- Docs y specs:

## Contrato

<!-- «No cambia», o qué endpoints, campos o errores cambian y si ya lo aprobó Felipe o Haider. -->

No cambia.

## Configuración

<!-- Variables de entorno nuevas (ya en .env.example), modos de desarrollo para saltarse pasos, dependencias nuevas y por qué. -->

Nada nuevo.

## Cómo probarlo

1. Comandos (migraciones, pipeline, variables):
2. Recorrido: entrar a …, hacer …, debe verse …

## Pruebas

- [ ] `pytest`, `ruff check` y `ruff format --check` en Docker
- [ ] `npm run typecheck`, `lint`, `format:check`, `test` y `build`
- [ ] `npm run test:responsive` con las rutas nuevas, y la pantalla completa en modo ligero
- [ ] Probado a mano de punta a punta

## Capturas

<!-- Escritorio y celular, si toca la web. -->

## Riesgos y pendientes

<!-- Qué quedó por fuera, supuestos y decisiones por confirmar. -->
