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

La documentación (`/api/docs` y `/api/openapi.json`, que usa `npm run api:types`) solo existe con
`AGROSENSE_API_DOCS=true`: lo trae `.env.example` y Docker Compose la enciende. Sin la variable queda apagada, y así
debe ir en producción.

## Dataset publicado

La API lee el dataset del pipeline de `AGROSENSE_DATA_DIR` (por defecto `data/published`, que también va dentro de la imagen).
Solo lo lee. Si no está, los catálogos y crear o editar un lote responden 503 `dataset_unavailable` y el log dice por qué;
lo demás sigue. Se publica con `uv run python -m pipeline.build` (`pipeline/README.md`).

## Precios de SIPSA al día (HU-222)

Con `AGROSENSE_MARKET_REFRESH=true` (Docker Compose lo trae encendido), la API baja los precios del DANE al arrancar si
lo que tiene es viejo y después cada día a las 3:00 p. m. de Bogotá (el DANE publica a las 2:00). Los valida con las
reglas del pipeline y los guarda como una versión nueva en `AGROSENSE_MARKET_DIR` (por defecto `data/market`, en el
volumen `market_data`). Si algo falla, sigue sirviendo la última versión buena y reintenta en una hora. Cada respuesta
de `/market/*` dice su `version` y su `updated_at` (R4). La descarga pesa unos 300 MB y tarda un par de minutos; la
API sigue atendiendo mientras tanto.

```bash
docker compose exec app python -m backend.market_updates   # bajar los precios ahora, sin esperar a las 3:00 p. m.
```

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
- Los eventos de más de 180 días se borran al arrancar la API y en cada inicio de sesión correcto.
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

- Una migración que ya está en `desarrollo` **no se edita**: otros ya la aplicaron. Lo que haya que corregir va en una migración nueva.
- Mientras la migración solo exista en su rama, sí puede rehacerla: `uv run python -m backend.db.migrate --bajar -1`, borre el archivo y créela otra vez.
- Un cambio de tablas es un cambio de contrato (`specs/02-contratos.md`): se avisa antes a Haider o a Felipe.

### Cuando dos personas crean una migración a la vez

Las dos toman el mismo número (por ejemplo `1.4`). Al juntar las ramas las pruebas fallan y el PR no pasa. Lo arregla
quien fusiona de segundo: baja la suya (`uv run python -m backend.db.migrate --bajar -1`), borra su archivo, trae `desarrollo` y la crea
otra vez con el comando, que ahora le da `1.5`.

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
| `uv run alembic upgrade head --sql` | Muestra el SQL sin ejecutarlo |
| `docker compose down -v` | Borra su base local; al volver a subirla, las migraciones la rehacen desde cero |

### Lo que cuidan las pruebas

`tests/accounts/test_migrations.py`: los modelos y las migraciones dicen lo mismo; hay una sola migración final; cada
archivo está en su carpeta, con su número, detrás de la anterior y sin saltos; todas bajan y vuelven a subir; y borrar un
usuario borra en cascada lo suyo (R9).

`tests/accounts/test_backup.py`: antes de migrar se copia la base y la copia sirve; si la copia falla no se migra; y
`alembic upgrade` directo se niega.

## Carpetas

```
backend/
├── db/              # de toda la base de datos: Base, conexión y migraciones de Alembic
│   └── migrations/  #     env.py y versions/: una sola historia para todas las tablas
├── accounts/        # M8: tablas (cuentas, finca, soporte y trazabilidad), contraseñas, sesiones y bitácora
├── api/             # M6: rutas, errores y la app de FastAPI
└── config/          # configuración por variables de entorno
tests/               # pytest; las de cuentas usan la base `<POSTGRES_DB>_test`
```
