# Backend de AgroSense

FastAPI + SQLAlchemy 2 + Alembic sobre PostgreSQL. Por ahora: el esquema completo de las cuentas (`backend/accounts/`) y la API de cuenta y sesión (`backend/api/`).

```bash
cp .env.example .env                           # una vez; el .env no va a git
docker compose up -d db                        # PostgreSQL local
uv sync                                        # entorno de Python
uv run python -m backend.db.migrate            # copia la base y crea o actualiza las tablas
uv run uvicorn backend.api.main:app --reload   # API en http://127.0.0.1:8000 (documentación en /api/docs)
```

O todo en Docker: `docker compose up app` copia la base, aplica las migraciones y deja la API en el mismo puerto.

La base del equipo y de la demo está en la nube: con `AGROSENSE_DATABASE_URL` en el `.env`, la API usa esa en vez de la
local (ver «Base de datos en la nube»). Las pruebas usan siempre la local.

La documentación (`/api/docs` y `/api/openapi.json`, que usa `npm run api:types`) solo existe con
`AGROSENSE_API_DOCS=true`: lo trae `.env.example` y Docker Compose la enciende. Sin la variable queda apagada, y así
debe ir en producción.

## Dataset publicado

La API lee el dataset del pipeline de `AGROSENSE_DATA_DIR` (por defecto `data/published`, que también va dentro de la imagen).
Solo lo lee. Si no está, los catálogos y crear o editar un lote responden 503 `dataset_unavailable` y el log dice por qué;
lo demás sigue. Se publica con `uv run python -m pipeline.build` (`pipeline/README.md`).

Al arrancar, la API también carga `grid_cells.parquet`, la rejilla de 250 m, pero solo las columnas `cell_id` y
`altitude_m` (unas 594 mil celdas, unos pocos MB en memoria). Con ella corrige la temperatura del municipio a la altitud
de un lote dibujado para decidir si el cultivo se da. Sin ese archivo, la aptitud de un lote con contorno queda como
`insufficient_data` y la respuesta lo dice en las limitaciones; no se usa la temperatura del municipio en su lugar.

Para programar contra datos sin esperar el pipeline: `AGROSENSE_DATA_DIR=data/examples` usa el dataset de ejemplo del
contrato (`uv run python -m pipeline.examples`, HU-011): tres municipios con cifras inventadas que citan la fuente `ejemplo`.

## Endpoints de cálculo (HU-012)

`/diagnostics`, `/rotations`, `/water-plans`, `/changes` y `/trends` ya tienen la forma del contrato
(`backend/api/calc_models.py`) y sus ejemplos de cada estado en el OpenAPI (`backend/api/calc_examples.py`). Validan la
entrada como dice el contrato (422, y 401 o 404 con `lot_id`) y, mientras el motor no exista, responden `501`
`not_implemented`. Cuando llega la HU del motor de cada uno, la ruta devuelve su modelo y la forma no cambia.

Los tipos de la web salen de este OpenAPI: con la API arriba y `AGROSENSE_API_DOCS=true`, `npm --prefix web run api:types`.

## Precios de SIPSA al día (HU-222)

La API **no baja nada ni calcula precios**: las rutas `GET /market/*` solo filtran por central o por producto y
devuelven. El último precio, el de hace una semana, el cambio y el orden vienen hechos en `market_price_latest`, que
escriben el pipeline y cada actualización. Qué versión se sirve lo decide el acceso a los datos, la dependencia
`market_tables` (`backend/market/store.py`): lee la última versión de `AGROSENSE_MARKET_DIR` (por defecto `data/market`,
en el volumen `market_data`) y vuelve a mirar `current.json` como mucho cada minuto, sin reiniciarse. Si no hay una
versión al menos tan nueva como el dataset publicado, sirve el publicado. Cada respuesta de `/market/*` dice su
`version`, su `updated_at`, la fuente del último día y su cita, que sale de la columna `citation` de `sources` (R4, R8).

Las versiones las escribe el servicio `market` de Docker Compose con dos crons (supercronic, hora de Bogotá, horarios del
`.env`), en `backend/market/updates.py`:

- **Diario** (`AGROSENSE_MARKET_DAILY_SCHEDULE`, de lunes a viernes a las 3:00 p. m.): el anexo del boletín diario del DANE,
  unos 340 KB, con el precio medio del día. Sin el mínimo ni el máximo (`source_id = dane_sipsa_boletin`).
- **Semanal** (`AGROSENSE_MARKET_WEEKLY_SCHEDULE`, los domingos a las 3:00 p. m.): la serie completa del servicio web de
  SIPSA, unos 300 MB, con el mínimo y el máximo. Reemplaza los días del boletín.

Las descargas cortan por tiempo total y por tamaño (`AGROSENSE_MARKET_TIMEOUT_S`, `AGROSENSE_MARKET_MAX_MB`). Si algo falla,
se sigue sirviendo la última versión buena y el log dice por qué. La temporada no se recalcula aquí: sale del dataset.

El servicio `market` **no usa la base de datos**: lee su configuración de `pipeline/settings.py`, no de
`backend/config/settings.py`, y no recibe las variables `POSTGRES_*`. Un candado (`data/market/.lock`) evita dos
actualizaciones a la vez; no se borra al arrancar: si un proceso murió con él puesto, se da por muerto a las 6 horas.

```bash
docker compose --profile market up -d market                                      # encender los crons
docker compose --profile market run --rm market python -m backend.market.updates diario    # el boletín, ya
docker compose --profile market run --rm market python -m backend.market.updates semanal   # la serie completa, ya
docker compose --profile market logs -f market                                    # ver qué hicieron
```

Sin el perfil `market` no arranca: en desarrollo no se usa la red y la API sirve los precios publicados.

## Seguridad de la cuenta

- Toda respuesta lleva `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy` y,
  por HTTPS, `Strict-Transport-Security`. Lo de la cuenta (`/api/v1/auth/*` y `/api/v1/me*`) va con `Cache-Control: no-store`.
- Límites (`backend/accounts/limits.py`): 5 contraseñas malas por usuario y conexión en 15 minutos (en memoria), 20 por
  usuario desde cualquier conexión (en `login_attempts`, sobrevive a un reinicio), 30 inicios de sesión y 10 registros por
  conexión, y 4 cálculos de Argon2 a la vez (si no, 503 `server_busy`). El intento se anota **antes** de verificar la
  contraseña: varias peticiones a la vez no se lo saltan. La IP nunca se guarda: en memoria queda solo su hash con una sal
  que cambia en cada arranque.
- Detrás de un proxy hay que darle a Uvicorn su dirección en `FORWARDED_ALLOW_IPS`, para que tome la IP real de
  `X-Forwarded-For`; si no, todas las personas parecen una sola conexión y se bloquean juntas.
- Borrar la cuenta (`DELETE /me`) pide la contraseña.
- Un bloqueo por intentos deja un solo evento `denied` en la actividad por ventana de 15 minutos, no uno por petición.
- Los eventos de más de 180 días y las sesiones vencidas los borra el mantenimiento de las cuentas: corre al arrancar la API y se puede programar una vez al día con `uv run python -m backend.accounts.maintenance`. Ningún endpoint limpia: cada uno hace solo lo suyo.
- Las copias de `backups/` quedan solo para el dueño (carpeta 700 y archivos 600; en Windows valen los permisos de su carpeta).
- El log nunca repite una dirección que no existe en la API (`route=[sin ruta]`) y escribe los caracteres de control
  como `\x1b`. Las trazas de errores de base de datos no llevan los valores de la consulta.

## La API sube siempre

La base de datos no tumba la API. Al arrancar se intenta copiar la base y migrar; pase lo que pase, la API sube.

| Situación | API | Lo que no usa la base de datos | Cuentas |
|---|---|---|---|
| Base arriba y esquema al día | Sube | Funciona | Funcionan |
| Base apagada o sin responder | Sube | Funciona | 503 `accounts_database_down` |
| La copia o una migración falló | Sube | Funciona | 503 `accounts_migration_pending` |

Las cuentas se habilitan solas cuando la base responde **y** está en la última migración que trae el código
(`backend/db/state.py`). Así nunca se atienden contra tablas que no son las que el código espera.

- A la persona se le dice lo mismo en los dos casos: «Las cuentas no están disponibles en este momento. Puede seguir
  consultando sin cuenta.»
- El motivo va al log, en cada intento de usar las cuentas:
  `accounts_unavailable … detail='Cuentas no disponibles (503) porque la migración 2.1 no se completó; la base de datos está en la 1.9'`
- `GET /api/v1/health` responde 200 con `accounts.available`, `reason`, `current_migration` y `expected_migration`.
- Para levantar la API sola, sin base: `docker compose up --no-deps app`.

Con la base apagada, la primera petición a las cuentas tarda unos 4 segundos en responder el 503: es lo que se
espera a la base antes de darla por caída. La API lo recuerda 10 segundos y, mientras tanto, responde el 503 al
instante sin volver a intentar conectarse. Pasados los 10 segundos, la siguiente petición vuelve a probar; así las
cuentas regresan solas a más tardar 10 segundos después de que vuelva la base.

## Logs

`structlog` a la salida estándar (HU-177): con color en desarrollo y una línea JSON por evento con
`AGROSENSE_LOG_FORMAT=json`. El nivel se elige con `AGROSENSE_LOG_LEVEL`. Cada petición deja una línea con su
`request_id`, método, ruta, estado y duración; nunca contraseñas, tokens ni polígonos. Para verlos: `docker compose logs -f app`.

Pruebas y lint, siempre en Docker:

```bash
docker compose run --rm app uv run pytest
docker compose run --rm app uv run ruff check .
```

## Migraciones

**La base de datos solo se cambia con una migración que queda en el repositorio.** Nadie crea ni altera tablas a mano.
Hay una sola historia de migraciones para toda la base de datos, en `backend/db/migrations/versions/`. En git van esos
archivos; los datos nunca.

### Cómo se numeran

Con dos números: `1.1`, `1.2` … hasta `1.9`, y después `2.1`. El primer número es la carpeta:

```
versions/
├── 1/
│   ├── 1.1_cuentas_usuarios_sesiones_e_intentos.py
│   ├── 1.2_finca_lotes_y_temporadas.py
│   ├── 1.3_soporte_trazabilidad_y_contador_de_uso.py
│   └── …            # hasta 1.9
└── 2/
    └── 2.1_….py     # la décima migración abre la carpeta 2
```

No hay nada que decidir: la siguiente migración es siempre el número que sigue, y al llenarse una carpeta (nueve
migraciones) se abre la otra sola. El número lo pone el comando, nunca usted.

### Copia de seguridad antes de cada migración

**Ninguna migración se aplica sin una copia de seguridad de la base de datos antes.** No depende de acordarse: las
migraciones se aplican con `python -m backend.db.migrate`, que primero copia la base y solo después migra.

- La copia queda en `backups/`, con un nombre que dice qué base, cuándo y entre qué migraciones:
  `agrosense_20261012-153000_de-1.3_a-1.4.dump`.
- Si la copia falla, **no se migra** (y en Docker la API no sube).
- `alembic upgrade` y `alembic downgrade` escritos a mano se niegan a correr y dicen qué comando usar.
- Vale igual para deshacer una migración (`--bajar`).
- Una base recién creada no tiene nada que copiar: es la única que migra sin copia.
- `backups/` no va a git ni a la imagen: tiene datos de cuentas. Se conservan las 20 copias más recientes.
- En un computador sin PostgreSQL instalado, la copia la hace el contenedor `db` de Docker Compose.

Para volver a una copia (borra lo que haya y deja la base como estaba):

```bash
docker compose exec -T db pg_restore -U agrosense -d agrosense --clean --if-exists --no-owner < backups/<archivo>.dump
```

### Si usted cambia la base de datos

1. Parta al día: `git pull` y `uv run python -m backend.db.migrate`.
2. Cambie los modelos (`backend/accounts/*models.py`). Un módulo nuevo con tablas se importa en `backend/db/models.py`.
3. Cree la migración:
   ```bash
   uv run python -m backend.db.revision "lo que cambia"
   ```
   El comando calcula el número, compara los modelos con su base de datos y deja el archivo en su carpeta.
4. **Lea el archivo.** La comparación automática no lo ve todo: un renombre lo escribe como borrar y crear (se pierden
   los datos) y no mueve datos. Corríjalo a mano si hace falta y revise que `downgrade()` deshaga lo que hace `upgrade()`.
5. Aplíquela: `uv run python -m backend.db.migrate`. Antes de tocar nada, copia su base a `backups/`.
6. Corra las pruebas. Suben la base desde cero con todas las migraciones, la bajan y la vuelven a subir.
7. Suba **en el mismo commit** el cambio de los modelos y el archivo de la migración.

Para una migración que solo mueve datos (sin cambio de modelos): `uv run python -m backend.db.revision "..." --vacia`.

### Si otra persona cambió la base de datos

`git pull` y `uv run python -m backend.db.migrate`. Nada más.

### Qué hace Docker y qué no

`docker compose up app` corre `python -m backend.db.migrate` al arrancar: copia la base y **aplica** las migraciones
que falten. Nunca **crea** migraciones: eso lo hace una persona, que la lee y la sube.

### Reglas

- Una migración que ya está en `desarrollo` **no se edita**: otros ya la aplicaron. Lo que haya que corregir va en una migración nueva. El PR que lo intente falla (ver «Migraciones con GitHub Actions»).
- **Compatible con el código de antes.** La base de la nube es una sola y la usan a la vez ramas con código viejo y nuevo. Agregar tablas, columnas que aceptan nulo o con valor por defecto, e índices: sí. Renombrar o borrar una columna o una tabla se hace en dos pasos: primero se deja de usar en el código, y en otra migración, después, se borra.
- Mientras la migración solo exista en su rama, sí puede rehacerla: `uv run python -m backend.db.migrate --bajar -1`, borre el archivo y créela otra vez.
- Un cambio de tablas es un cambio de contrato (`specs/02-contratos.md`): se avisa antes a Haider o a Felipe.

### Cuando dos personas crean una migración a la vez

Las dos toman el mismo número (por ejemplo `1.4`). La primera que se fusiona gana. La segunda falla en su PR: «hay 2
migraciones finales». Lo arregla quien llega de segundo, según el tipo de choque:

- **Solo el número** (las dos cambian tablas distintas): traiga `desarrollo` y renumere la suya.
  ```bash
  git fetch && git merge origin/desarrollo
  python -m backend.db.renumber      # su 1.4 pasa a 1.5, detrás de la que ya se fusionó
  ```
  Corre con el Python de su computador (solo usa la biblioteca estándar y git): no necesita Docker ni `uv`.
  Si su base local ya tenía aplicada su `1.4`, rehágala: `docker compose down -v`, `docker compose up -d db` y
  `uv run python -m backend.db.migrate`.
- **El contenido** (las dos cambian la misma tabla): renumerar no basta. Las pruebas fallan porque la suya no corre
  detrás de la otra, o porque los modelos ya no coinciden. Borre su archivo, traiga `desarrollo`, rehaga su base local,
  ajuste los modelos y créela otra vez con `uv run python -m backend.db.revision "..."`, que ahora le da `1.5` y la
  compara contra la tabla ya cambiada.

En los dos casos, el PR vuelve a correr las pruebas y solo pasa cuando su migración va detrás de la otra y corre bien.

### Comandos

| Comando | Qué hace |
|---|---|
| `uv run python -m backend.db.revision "..."` | Crea la siguiente migración, con su número y en su carpeta |
| `uv run python -m backend.db.migrate` | Copia la base y aplica lo que falte |
| `uv run alembic current` | Dice en qué migración está su base |
| `uv run alembic history` | Lista las migraciones, de la última a la primera |
| `uv run alembic check` | Falla si los modelos tienen cambios sin migración |
| `uv run python -m backend.db.migrate --bajar -1` | Copia la base y deshace la última |
| `uv run python -m backend.db.migrate --bajar 1.2` | Copia la base y vuelve a como quedó tras esa migración |
| `python -m backend.db.renumber` | Pasa sus migraciones detrás de las de `origin/desarrollo` (choque de número); sin Docker ni `uv` |
| `uv run alembic upgrade head --sql` | Muestra el SQL sin ejecutarlo |
| `docker compose down -v` | Borra su base local; al volver a subirla, las migraciones la rehacen desde cero |

### Lo que cuidan las pruebas

`tests/accounts/test_migrations.py`: los modelos y las migraciones dicen lo mismo; hay una sola migración final; cada
archivo está en su carpeta, con su número, detrás de la anterior y sin saltos; todas bajan y vuelven a subir; y borrar un
usuario borra en cascada lo suyo (R9).

`tests/accounts/test_backup.py`: antes de migrar se copia la base y la copia sirve; si la copia falla no se migra; y
`alembic upgrade` directo se niega.

`tests/accounts/test_base_en_la_nube.py`: la cadena de la nube se usa con psycopg y SSL; la base de la nube no se migra
sola al arrancar; su copia viaja con el mismo SSL; y las pruebas nunca la usan.

## Base de datos en la nube

Desde el 10 de noviembre de 2026 la base del equipo y de la demo es un PostgreSQL 17 en la nube
(`docs/registro-de-decisiones.md`). La de Docker Compose (`db`) sigue siendo la de las pruebas y la de trabajar sin conexión.

**Cómo conectarse.** Copie la cadena de conexión, con la clave, en su `.env`:

```bash
AGROSENSE_DATABASE_URL=postgresql://<usuario>:<clave>@<host>:5432/<base>
```

- Sin `sslmode` en la cadena, la API exige SSL (`sslmode=require`). La copia de seguridad viaja con el mismo SSL.
- Si la cadena está mal escrita (con comillas, con el nombre de la variable delante, sin `postgresql://`, sin la base o
  con caracteres de la clave sin codificar), la API y el workflow no arrancan y dicen qué revisar, **sin repetir la
  cadena**: trae la clave, y los logs de GitHub Actions son públicos. Los espacios y el salto de línea de los bordes se
  quitan solos.
- La cadena trae la clave: va solo en su `.env` o en el panel del alojamiento. Nunca en git, en un chat ni en un issue.
- Sin la variable (o vacía), todo vuelve a la base local.

**Las pruebas nunca la usan.** `tests/conftest.py` reemplaza la cadena por la base local durante `pytest`, venga de
Compose o del `.env`, y se niega a correr si `POSTGRES_HOST` no es local: las pruebas crean una base y borran su
esquema en cada corrida.

**La API no la migra al arrancar.** Con la base de la nube, la API **no** aplica migraciones al arrancar: es compartida,
y una rama con una migración nueva cambiaría la base de todo el equipo. Al arrancar solo dice si falta alguna
(`migration_pending`) y, mientras falte, las cuentas quedan apagadas. Las migraciones las aplica **GitHub Actions al
fusionar en `desarrollo`** (ver «Migraciones con GitHub Actions»). A mano, solo si el workflow no puede:

```bash
docker compose run --rm app python -m backend.db.migrate   # dice «Base de datos: en la nube», copia y migra
```

Se corre desde la imagen de la app porque trae `pg_dump` 17, el mismo del servidor. El contenedor `db` no sirve para
copiar la nube: solo alcanza la base local, y por eso `migrate` se niega.

**La copia trae datos personales.** Queda en `backups/` de quien migra, con todas las cuentas. No la comparta ni la suba
a ningún lado; borre las que ya no sirvan.

## Migraciones con GitHub Actions

`.github/workflows/migraciones.yml` (HU-229) hace dos trabajos.

**En cada PR hacia `desarrollo` o `produccion`** (sin secretos, con un PostgreSQL temporal en Docker):

1. Si el PR no toca el backend, termina en verde.
2. Falla si el PR edita, borra o renombra una migración que ya está en la rama de destino.
3. Corre en Docker las pruebas de las migraciones **sobre el código ya fusionado con la rama de destino**: una sola
   migración final, números sin saltos, modelos y migraciones iguales, cada una baja y vuelve a subir, y la copia antes de
   migrar. Si otra migración se fusionó primero, aquí aparece el choque (ver «Cuando dos personas crean una migración a
   la vez»).
4. Si el PR trae migraciones nuevas, deja un comentario con cuáles son y el SQL que van a ejecutar
   (`python -m backend.db.report`, sin conectarse a ninguna base). Revíselo antes de fusionar.

**Al fusionar en `desarrollo`** un cambio en `backend/db/migrations/versions/`:

1. Construye la imagen de la app y corre `python -m backend.db.migrate` contra la base de la nube: copia y migra.
2. De a una corrida a la vez (nunca dos sobre la misma base) y sin cortar una que ya empezó.
3. Cifra la copia con AES-256 y la guarda 7 días como archivo del workflow. Sin la clave de cifrado no migra. El
   repositorio es público: nunca queda una copia sin cifrar, y el host y el usuario de la base se tapan en los logs.

Para recuperar una copia: descargue el archivo del workflow y descífrelo con la clave.

```bash
gpg --decrypt agrosense_<fecha>_de-1.3_a-1.4.dump.gpg > copia.dump
```

También se puede correr a mano desde *Actions* → *Migraciones* → *Run workflow*, sobre `desarrollo`.

### Lo que configura el dueño del repositorio

Solo el dueño puede hacerlo (*Settings* del repositorio):

1. **Entorno `nube`** (*Environments*): los secretos `AGROSENSE_DATABASE_URL` (la cadena de conexión de la base de la
   nube) y `AGROSENSE_BACKUP_KEY` (una clave larga para cifrar las copias; guárdela fuera de GitHub, sin ella no se
   puede abrir una copia). Si quiere aprobar cada migración antes de que corra, agregue revisores al entorno.
2. **Reglas de la rama `desarrollo`** (*Branches* o *Rules*): exigir el check «Revisar migraciones» y que la rama esté
   al día antes de fusionar. Sin lo segundo, un PR viejo se fusiona sin volver a probarse contra la migración nueva.
3. Opcional: exigir la revisión de los dueños del código (`.github/CODEOWNERS`): los cambios de migraciones son cambios
   de contrato y los revisan Haider o Felipe.

## Carpetas

```
backend/
├── db/              # de toda la base de datos: Base, conexión y migraciones de Alembic
│   └── migrations/  #     env.py y versions/: una sola historia para todas las tablas
├── accounts/        # M8: tablas (cuentas, finca, soporte y trazabilidad), contraseñas, sesiones y bitácora
├── api/             # M6: rutas, errores y la app de FastAPI; calc_models.py y calc_examples.py: el contrato de cálculo
├── engine/          # M1–M11: el motor puro, sin FastAPI ni archivos (R6)
└── config/          # configuración por variables de entorno
tests/               # pytest; las de cuentas usan la base `<POSTGRES_DB>_test`
```
