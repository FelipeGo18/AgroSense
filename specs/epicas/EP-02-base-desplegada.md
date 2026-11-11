---
id: EP-02
titulo: "Base del proyecto desplegada"
prioridad: P0
fase: [Hora 0]
rol: "Plataforma (Motor y API si el equipo es de 4)"
agentes: [plataforma]
subsistemas: [S1, S2]
depende_de: []
reglas: [R4, R9]
estado: pendiente
---

# EP-02 · Base del proyecto desplegada

**Resultado esperado:** Cualquier integrante arranca el proyecto en minutos, y la URL pública existe desde las primeras horas.

## Historias de usuario

### HU-021 · Clonar y ejecutar con pocos comandos

- **Historia:** Como integrante, quiero clonar y ejecutar todo con pocos comandos, para no perder tiempo configurando.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [X] README de arranque probado por otra persona. Escrito el 12 de octubre de 2026 (`README.md`, «Cómo correr el proyecto», con Docker y sin Docker); «Probado con y sin Docker en dos máquinas (`docs/reporte-prueba-hu-021.md`)»
  - [X] Estructura del repositorio acordada

### HU-022 · Lint y pruebas automáticas en cada cambio

- **Historia:** Como equipo, quiero lint y pruebas automáticas en cada cambio, para detectar roturas temprano.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] GitHub Actions corre Ruff, pytest, Vitest y el build web dentro de Docker Compose
  - [ ] Las mismas pruebas corren en local con un solo comando de Docker

### HU-177 · Logs de la terminal

- **Historia:** Como equipo, queremos logs claros en la terminal del backend y del pipeline, para saber qué pasa en el servidor y diagnosticar un fallo durante la demo.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** en curso
- **Criterios de aceptación:**
  - [x] `structlog` configurado una vez y usado por la API, el pipeline y los avisos de Uvicorn (el log de acceso propio de Uvicorn se apaga): `common/logging.py` (antes `backend/config/logging.py`; se movió el 9 de noviembre de 2026 para que el pipeline no importe el backend), también para las migraciones y, desde el 8 de noviembre de 2026, para `pipeline.build`, que lee solo `AGROSENSE_LOG_LEVEL` y `AGROSENSE_LOG_FORMAT` (no necesita la base de datos)
  - [x] En desarrollo, líneas legibles con color; en producción, una línea JSON por evento a la salida estándar (Docker la recoge). Sin archivos de log
  - [x] Cada petición deja una línea con los campos de «Logs de la terminal» del contrato; el `request_id` sale en la cabecera `X-Request-ID`
  - [x] Niveles: `DEBUG` solo en desarrollo; `INFO` por defecto; `WARNING` para todo lo rechazado (`400` a `499`) y `503`; `ERROR` para `500`, con la traza del error
  - [x] Cada línea explica qué pasó en palabras (`detail`) y dice qué endpoint atendió (`endpoint`); en la consola, el nivel, el mensaje, el código y el endpoint van cada uno en su color
  - [x] Un procesador de redacción borra de cualquier evento las llaves `password`, `token`, `cookie`, `authorization` y `geometry`; una prueba lo comprueba
  - [x] Cuando las cuentas están apagadas, el log dice por qué: la base de datos no responde, o qué migración no se completó y en cuál está la base
  - [ ] Los cuerpos de los endpoints de cálculo no se escriben en el log (R9); se registra solo la ruta, el estado, la duración y las versiones del dataset y de las reglas
  - [x] El pipeline registra cada paso con la fuente, filas leídas, filas rechazadas y el motivo: `source_read` por fuente (`rows_read`, `rows_kept`, `rows_rejected` y `reasons`: `outside_region` en DIVIPOLA; `other_market` y `no_average` en SIPSA), `table_written` por tabla y, al final, `dataset_published` o `dataset_not_published` con el motivo (`tests/pipeline/test_reconstruir.py`)
  - [x] Nivel y formato se eligen con `AGROSENSE_LOG_LEVEL` y `AGROSENSE_LOG_FORMAT` (`console` o `json`)
- **Reglas que aplican:** R4, R9
- **Notas:** Los logs de la terminal son para operar el servidor y no se consultan desde la web; lo que hace cada usuario va en la trazabilidad de la base de datos (HU-178). La web no envía logs al servidor ni a servicios de terceros. Definido el 10 de octubre de 2026. Desde el 8 de noviembre de 2026 solo falta el criterio de los endpoints de cálculo, que se cumple cuando existan (EP-07, EP-08).

### HU-023 · Esqueleto desplegado en URL pública

- **Historia:** Como equipo, quiero el esqueleto desplegado, para que el despliegue no sea un riesgo al final.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Un contenedor sirve API y web en una URL pública
  - [ ] `/api/v1/version` responde
  - [ ] La app desplegada usa la base de datos en la nube (`AGROSENSE_DATABASE_URL` en el panel del alojamiento); credenciales en variables de entorno, ningún secreto en el repositorio
- **Notas:** Desde el 10 de noviembre de 2026 la base del despliegue es la de la nube, no un PostgreSQL con volumen (`docs/registro-de-decisiones.md`). Sus migraciones las aplica GitHub Actions al fusionar en `desarrollo` (HU-229).

### HU-229 · Migraciones revisadas y aplicadas con GitHub Actions

- **Historia:** Como equipo, quiero que cada cambio de la base de datos se revise solo en el PR y se aplique solo a la base de la nube al fusionar, para que dos cambios de la misma tabla no choquen y nadie tenga que acordarse de migrar.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** en curso
- **Criterios de aceptación:**
  - [ ] En cada PR hacia `desarrollo` o `produccion` que toque el backend, un workflow corre en Docker las pruebas de las migraciones sobre el código ya fusionado con la rama de destino: una sola migración final, números sin saltos ni repetidos, modelos y migraciones iguales, cada una baja y vuelve a subir, y la copia de seguridad antes de migrar
  - [ ] El PR falla si edita, borra o renombra una migración que ya está en la rama de destino
  - [ ] Si el PR trae migraciones nuevas, un comentario del workflow dice cuáles son y su SQL, para revisarlas antes de fusionar
  - [ ] Al fusionar en `desarrollo` un cambio de migraciones, el workflow las aplica a la base de la nube con la imagen de la app (`pg_dump` 17), de a una corrida a la vez y con copia de seguridad antes
  - [ ] La copia sale cifrada (AES-256) y queda 7 días como archivo del workflow; sin la clave de cifrado no se migra. El repositorio es público: nunca hay una copia sin cifrar ni un dato de conexión en los logs
  - [ ] `python -m backend.db.renumber` pasa las migraciones propias de la rama al número que sigue a las de la rama de destino y las encadena detrás de la última
  - [ ] `backend/README.md` explica el flujo, cómo resolver un choque de migraciones y lo que configura el dueño del repositorio (secretos, entorno `nube` y reglas de la rama)
- **Reglas que aplican:** R4, R9
- **Notas:** Decidido el 10 de noviembre de 2026: las migraciones se aplican solas al fusionar. La base de la nube es una sola, así que una migración tiene que ser compatible con el código que todavía no se actualizó: agregar tablas o columnas sí; renombrar o borrar se hace en dos pasos. Un choque de contenido (dos migraciones que cambian la misma tabla) no se arregla renumerando: la del PR se rehace sobre la rama de destino. Agregada el 10 de noviembre de 2026.
