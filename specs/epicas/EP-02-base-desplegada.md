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
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [X] GitHub Actions corre Ruff, pytest, Vitest y el build web dentro de Docker Compose
  - [X] Las mismas pruebas corren en local con un solo comando de Docker

### HU-177 · Logs de la terminal

- **Historia:** Como equipo, queremos logs claros en la terminal del backend y del pipeline, para saber qué pasa en el servidor y diagnosticar un fallo durante la demo.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] `structlog` configurado una vez y usado por la API, el pipeline y los avisos de Uvicorn (el log de acceso propio de Uvicorn se apaga): `common/logging.py` (antes `backend/config/logging.py`; se movió el 9 de noviembre de 2026 para que el pipeline no importe el backend), también para las migraciones y, desde el 8 de noviembre de 2026, para `pipeline.build`, que lee solo `AGROSENSE_LOG_LEVEL` y `AGROSENSE_LOG_FORMAT` (no necesita la base de datos)
  - [x] En desarrollo, líneas legibles con color; en producción, una línea JSON por evento a la salida estándar (Docker la recoge). Sin archivos de log
  - [x] Cada petición deja una línea con los campos de «Logs de la terminal» del contrato; el `request_id` sale en la cabecera `X-Request-ID`
  - [x] Niveles: `DEBUG` solo en desarrollo; `INFO` por defecto; `WARNING` para todo lo rechazado (`400` a `499`) y `503`; `ERROR` para `500`, con la traza del error
  - [x] Cada línea explica qué pasó en palabras (`detail`) y dice qué endpoint atendió (`endpoint`); en la consola, el nivel, el mensaje, el código y el endpoint van cada uno en su color
  - [x] Un procesador de redacción borra de cualquier evento las llaves `password`, `token`, `cookie`, `authorization` y `geometry`; una prueba lo comprueba
  - [x] Cuando las cuentas están apagadas, el log dice por qué: la base de datos no responde, o qué migración no se completó y en cuál está la base
  - [x] Los cuerpos de los endpoints de cálculo no se escriben en el log (R9); se registra solo la ruta, el estado, la duración y las versiones del dataset y de las reglas
  - [x] El pipeline registra cada paso con la fuente, filas leídas, filas rechazadas y el motivo: `source_read` por fuente (`rows_read`, `rows_kept`, `rows_rejected` y `reasons`: `outside_region` en DIVIPOLA; `other_market` y `no_average` en SIPSA), `table_written` por tabla y, al final, `dataset_published` o `dataset_not_published` con el motivo (`tests/pipeline/test_reconstruir.py`)
  - [x] Nivel y formato se eligen con `AGROSENSE_LOG_LEVEL` y `AGROSENSE_LOG_FORMAT` (`console` o `json`)
- **Reglas que aplican:** R4, R9
- **Notas:** Los logs de la terminal son para operar el servidor y no se consultan desde la web; lo que hace cada usuario va en la trazabilidad de la base de datos (HU-178). La web no envía logs al servidor ni a servicios de terceros. Definido el 10 de octubre de 2026. Desde el 8 de noviembre de 2026 solo falta el criterio de los endpoints de cálculo, que se cumple cuando existan (EP-07, EP-08). **14 de noviembre de 2026 (hecho):** los endpoints de cálculo ya existen (responden `501` mientras no esté su parte del motor, y el diagnóstico responde `200` cuando el cultivo no es apto). Su dependencia `calc_dataset` (`backend/api/calculations.py`) deja en la petición las versiones del dataset y de las reglas, y la línea `request` las escribe como `dataset` y `rules` (R4); sin dataset (`503`) no van, nunca inventadas. El cuerpo y los parámetros de la consulta nunca se escriben: la línea lleva la plantilla de la ruta. `tests/test_logs_de_calculo.py` lo comprueba en los cinco endpoints: ni el municipio, ni el cultivo, ni la fecha ni el área aparecen en el log.

### HU-023 · La app desplegada en Google Cloud Run

- **Historia:** Como equipo y como jurado, queremos AgroSense publicado en una dirección pública, para que el despliegue no sea un riesgo al final y la demo corra contra lo de verdad.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] La imagen de la app (`Dockerfile`: FastAPI sirve la API y el build de la web, con `data/published` adentro) corre en **Google Cloud Run**, en la región `us-east1` (la de la capa gratuita de la base, HU-234), en un proyecto de Google Cloud de un integrante con el crédito del evento (300 USD por 90 días, sin cobro automático al terminar)
  - [ ] `/api/v1/version` responde en la dirección pública y dice la versión del dataset y de las reglas (R4)
  - [ ] La app usa la base de **producción** (HU-234), nunca la del equipo ni la de Docker; `AGROSENSE_DATABASE_URL` sale de **Secret Manager**, no de una variable escrita a mano ni del repositorio
  - [ ] Producción: `AGROSENSE_API_DOCS` apagado (sin `/api/docs` ni `/api/openapi.json`), logs en JSON (HU-177), y los endpoints de cálculo no escriben nada en la base (R9)
  - [ ] Cloud Run con al menos una instancia caliente mientras dure el juzgamiento (`min-instances` 1), para que el jurado no espere un arranque en frío; después vuelve a 0 para no gastar el crédito
  - [ ] `backend/README.md` dice cómo está desplegada, qué configura el dueño del proyecto de Google Cloud y cómo volver a la versión anterior
- **Reglas que aplican:** R4, R9
- **Contrato que toca:** ninguno
- **Notas:** Cambiada el 14 de noviembre de 2026 (decidido por Felipe): el evento regala créditos de Google Cloud y de Azure, y un dominio de GoDaddy Registry con Porkbun (`docs/registro-de-decisiones.md`). Se eligió Google Cloud porque su crédito dura 90 días y no cobra solo al terminar. El hosting de GoDaddy no corre Docker ni Python: solo se usa su dominio (HU-236). Asignada a Haider y David Carreño.

### HU-234 · La base de datos de producción

- **Historia:** Como equipo, queremos una base de datos solo para la app publicada, separada de la del equipo, para que la demo y el jurado no vean datos de prueba y lo que se pruebe en desarrollo no toque producción.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] **PostgreSQL 17** en una VM **e2-micro de Compute Engine** (capa gratuita; Cloud SQL no la tiene), en el mismo proyecto y la misma región que Cloud Run, sin puerto público (solo Cloud Run llega, por la red privada), con SSL obligatorio y clave `scram-sha-256`
  - [ ] Copias de seguridad diarias **fuera de la VM**, en un bucket privado de Cloud Storage, por 7 días; y la VM protegida contra el borrado (`deletion_protection` y `prevent_destroy`), porque sus datos viven en su disco
  - [ ] Un usuario propio de la app, con permisos solo sobre su base; otro usuario para las migraciones (HU-235). Ninguna contraseña en el repositorio: van en Secret Manager (GitHub entra con Workload Identity Federation, sin secretos)
  - [ ] Las migraciones de Alembic dejan el esquema igual que en `desarrollo`; la base empieza vacía de cuentas (sin copiar la del equipo)
  - [ ] La base del equipo (`AGROSENSE_DATABASE_URL` de hoy) sigue para el desarrollo y la demo interna, y la de Docker Compose para las pruebas, que nunca usan una base en la nube
  - [ ] Borrar una cuenta en producción borra todo lo suyo (R9), como en las pruebas
- **Reglas que aplican:** R9
- **Contrato que toca:** ninguno
- **Notas:** Decidido por Felipe el 14 de noviembre de 2026: la demo y el enlace de la entrega van contra la base de producción. Asignada a Haider y David Carreño. **15 de noviembre de 2026 (propuesta de David, pendiente de aprobar por Felipe):** la base de producción es PostgreSQL 17 en una VM e2-micro de Compute Engine (`infra/`, Terraform) y no Cloud SQL, porque Cloud SQL no tiene capa gratuita y la VM sí (us-east1). Sin puerto público: solo Cloud Run llega por la red privada, con SSL y clave. Copia diaria con `pg_dump`, 7 días, en la VM y en el bucket de copias. Un solo usuario (`agrosense`) para la app y las migraciones: separar el de migraciones queda pendiente. Los criterios de la base y de las copias se reescribieron para la VM (antes, uno solo: «una instancia de Cloud SQL con PostgreSQL 17, la más pequeña, con SSL obligatorio y copias automáticas diarias»), y el de las contraseñas ya no habla de secretos de GitHub (entra con Workload Identity Federation); también pendientes de Felipe.

### HU-235 · Desplegar al fusionar en `produccion`

- **Historia:** Como equipo, queremos que fusionar en `produccion` publique solo la app, con sus migraciones, para que nadie despliegue a mano el día de la entrega.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Un workflow de GitHub Actions que corre al fusionar en `produccion` (y a mano, con `workflow_dispatch`), de a una corrida a la vez: construye la imagen, la sube a **Artifact Registry** con la etiqueta del commit, aplica las migraciones a la base de producción (HU-234) y despliega en Cloud Run
  - [ ] Antes de migrar, una copia de seguridad de la base de producción en el bucket privado de copias (HU-234), cifrada en reposo por Google, por 7 días; si no sube completa, no se migra. Nunca un dato de conexión ni una copia en los logs (el repositorio es público)
  - [ ] Se conecta a Google Cloud con **Workload Identity Federation** (sin llaves JSON guardadas en GitHub), con una cuenta de servicio que solo puede subir imágenes y desplegar ese servicio
  - [ ] Después de desplegar, comprueba `/api/v1/version` en la dirección pública y que la versión sea la del commit; si falla, Cloud Run vuelve a la revisión anterior y el workflow termina en rojo
  - [ ] El entorno `produccion` de GitHub pide la aprobación de un responsable (Felipe o Haider) antes de desplegar
  - [ ] Los checks obligatorios de `produccion` son los mismos de `desarrollo` (`hu`, `python`, `web`, `Revisar migraciones`). En el PR de `desarrollo` a `produccion`, `hu` no revisa los nombres: los commits ya se revisaron al entrar a `desarrollo` (`docs/registro-de-decisiones.md`, 15 nov)
  - [ ] **Logs en Cloud Logging.** El servicio corre con `AGROSENSE_LOG_FORMAT=json` y `AGROSENSE_LOG_LEVEL=INFO`, y cada línea JSON (`common/logging.py`) trae:
    - `severity` (`DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL`), además de `level`. Sin ese campo, Cloud Logging marca todo como `DEFAULT` y no se puede filtrar por nivel;
    - `message`, con el evento, para que se lea como el resumen de la línea;
    - `logging.googleapis.com/trace` (`projects/<proyecto>/traces/<trace_id>`), tomado del encabezado `X-Cloud-Trace-Context`, para que las líneas de una petición se vean juntas con la petición de Cloud Run aun con muchas peticiones a la vez. Sin ese encabezado (local, pruebas) el campo no va
  - [ ] Prueba: con `json`, una línea de error trae `severity = ERROR` y `message`, y con el encabezado, el trace. Los secretos siguen redactados y una consulta de cálculo no escribe datos de la finca en los logs (R9)
- **Reglas que aplican:** R4, R9
- **Contrato que toca:** ninguno
- **Notas:** Sigue el flujo de HU-229, que aplica las migraciones a la base del equipo al fusionar en `desarrollo`. Una migración tiene que ser compatible con el código anterior (agregar sí; renombrar o borrar, en dos pasos), porque la base se migra antes de que la nueva versión reemplace a la vieja. Los criterios de los logs se agregaron el 14 de noviembre de 2026 (Felipe, revisión del #89): el `request_id` de `common/logging.py` sigue igual; el trace es lo que Cloud Logging usa para agrupar. Asignada a Haider y David Carreño. **15 de noviembre de 2026 (PR #181):** el workflow `deploy-produccion.yml` construye, sube, migra con copia en Cloud Storage, despliega, comprueba que sirve la revisión del commit y vuelve atrás si falla. La copia ya no se cifra con `gpg` como en HU-229 (el job de Cloud Run no tiene disco que dure): va al bucket privado, cifrada en reposo por Google y sin que el job la pueda leer ni borrar; pendiente de aprobar por Felipe con HU-234. **Falta:** los logs para Cloud Logging (`severity`, `message` y el trace no están en `common/logging.py`), y lo que configura el dueño del repositorio: el entorno `produccion` con aprobación y los checks obligatorios de `produccion` (`backend/README.md`).

### HU-236 · El dominio con HTTPS

- **Historia:** Como jurado y como agricultor, quiero entrar a AgroSense por una dirección corta y segura, para confiar en el enlace y compartirlo.
- **Prioridad:** P0 · **Tamaño:** S · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Un dominio gratis de la oferta de GoDaddy Registry (registrado en Porkbun, por un año, no premium), a nombre del equipo; su DNS apunta a Cloud Run con el mapeo de dominio, y el certificado HTTPS es el que maneja Google
  - [ ] Todo lo que entre por HTTP se redirige a HTTPS; la cookie de sesión va `Secure`, `HttpOnly` y `SameSite=Lax`, y la API solo acepta el dominio propio como origen
  - [ ] El enlace de la entrega es el dominio con `?lang=en` (HU-233), público y sin inicio de sesión, y se pide la clasificación de FortiGuard que recomienda la guía de entrega, para que el jurado pueda abrirlo
  - [ ] Si el dominio no queda a tiempo, el enlace de la entrega es la dirección de Cloud Run (`*.run.app`)
- **Reglas que aplican:** R9
- **Contrato que toca:** ninguno
- **Notas:** La oferta de GoDaddy Registry da el dominio, un año de hosting y SSL; solo se usa el dominio (la app va en Cloud Run). Asignada a Haider y David Carreño.

### HU-229 · Migraciones revisadas y aplicadas con GitHub Actions

- **Historia:** Como equipo, quiero que cada cambio de la base de datos se revise solo en el PR y se aplique solo a la base de la nube al fusionar, para que dos cambios de la misma tabla no choquen y nadie tenga que acordarse de migrar.
- **Prioridad:** P0 · **Tamaño:** M · **Estado:** hecha
- **Criterios de aceptación:**
  - [x] En cada PR hacia `desarrollo` o `produccion` que toque el backend, un workflow corre en Docker las pruebas de las migraciones sobre el código ya fusionado con la rama de destino: una sola migración final, números sin saltos ni repetidos, modelos y migraciones iguales, cada una baja y vuelve a subir, y la copia de seguridad antes de migrar
  - [x] El PR falla si edita, borra o renombra una migración que ya está en la rama de destino
  - [x] Si el PR trae migraciones nuevas, un comentario del workflow dice cuáles son y su SQL, para revisarlas antes de fusionar
  - [x] Al fusionar en `desarrollo` un cambio de migraciones, el workflow las aplica a la base de la nube con la imagen de la app (`pg_dump` 17), de a una corrida a la vez y con copia de seguridad antes
  - [x] La copia sale cifrada (AES-256) y queda 7 días como archivo del workflow; sin la clave de cifrado no se migra. El repositorio es público: nunca hay una copia sin cifrar ni un dato de conexión en los logs
  - [x] `python -m backend.db.renumber` pasa las migraciones propias de la rama al número que sigue a las de la rama de destino y las encadena detrás de la última
  - [x] `backend/README.md` explica el flujo, cómo resolver un choque de migraciones y lo que configura el dueño del repositorio (secretos, entorno `nube` y reglas de la rama)
- **Reglas que aplican:** R4, R9
- **Notas:** Decidido el 10 de noviembre de 2026: las migraciones se aplican solas al fusionar. La base de la nube es una sola, así que una migración tiene que ser compatible con el código que todavía no se actualizó: agregar tablas o columnas sí; renombrar o borrar se hace en dos pasos. Un choque de contenido (dos migraciones que cambian la misma tabla) no se arregla renumerando: la del PR se rehace sobre la rama de destino. Agregada el 10 de noviembre de 2026.
- **Verificado (14 nov):** en un PR borrador de prueba (#68, cerrado sin fusionar) con una migración `1.4` que solo hace `SELECT 1`: la revisión corre en Docker sobre el código fusionado, el bot comentó la `1.4` con su SQL, y al editar la `1.3` ya fusionada el paso «Las migraciones fusionadas no se tocan» falló y nombró el archivo. La prueba encontró un error: `test_backup.py`, `test_base_en_la_nube.py` y `test_disponibilidad.py` tenían fija la última migración (`1.3`), así que todo PR con una migración nueva fallaba aunque estuviera bien; ahora leen la última del código (`expected_revision()`). Con el arreglo, las 656 pruebas pasan con la `1.4`. `renumber` lo cubren sus pruebas (`test_renumerar.py`), que corren en cada PR. El 10 de noviembre el workflow conectó con la base de la nube (con los secretos del entorno `nube` y los datos de conexión tapados en el log), pero la base ya estaba al día, así que no hubo copia.
- **Verificado (15 nov), con dos migraciones reales en la base de la nube:** al fusionar el #134 (HU-178, migración `1.4`, «actividad protegida»; corrida 43679884646, 05:10 UTC) y el #130 (HU-163, migración `1.5`, «respuesta de los mensajes»; corrida 43721750521, 13:58 UTC), el trabajo «Aplicar en la base de la nube» terminó bien. En las dos:
  - **Copia y migración con la imagen de la app:** `python -m backend.db.migrate` corre en la imagen de la app que construye la misma corrida con el `Dockerfile` (`python:3.12-slim` sobre Debian 13, cuyo `postgresql-client` trae `pg_dump` 17: en la imagen local da 17.11) y hace la copia antes de migrar (`backup` antes de `command.upgrade`, `backend/db/migrate.py`). El log dice `Running upgrade 1.3 -> 1.4` y `1.4 -> 1.5`, y las copias se llaman `postgres_20261115-051124_de-1.3_a-1.4.dump` y `postgres_20261115-135854_de-1.4_a-1.5.dump`.
  - **De a una corrida a la vez:** `concurrency` con el grupo `migraciones-nube` y `cancel-in-progress: false` (no corta una que ya empezó).
  - **Copia cifrada, 7 días:** `gpg --symmetric --cipher-algo AES256` con `AGROSENSE_BACKUP_KEY`, y el archivo `copia-base-nube-<corrida>` sube solo `backups/*.gpg` con `retention-days: 7` (vencen el 22 de noviembre). Sin `AGROSENSE_DATABASE_URL` o sin `AGROSENSE_BACKUP_KEY`, el paso «Secretos del entorno nube» falla antes de migrar.
  - **Nada en los logs:** los dos secretos salen como `***`, la línea de la base dice «en la nube (\*\*\*, base postgres)» y ningún log trae una cadena de conexión.

  Lo que no se comprobó: abrir una copia con `gpg --decrypt`, porque la clave la tiene solo el dueño del repositorio.
