# Reporte de prueba — HU-021: Clonar y ejecutar con pocos comandos

- **Fecha:** 10 de noviembre de 2026
- **Propósito:** probar los pasos de «Cómo correr el proyecto» del README.
- **Estado general:** Resuelto.

## Con Docker

### 1. Requisitos previos
- Tener git instalado (https://git-scm.com/). Se prueba con git v2.53.0
- Instalar Docker Desktop (https://www.docker.com/products/docker-desktop/) y abrirlo antes de empezar. Se prueba con docker v29.9.3
- Instalar node.js (https://nodejs.org/) en una versión igual o superior a la 22. Se prueba con node v26.13.0
- Instalar uv (https://docs.astral.sh/uv/) en una versión igual o superior a la 0.13. Se prueba con uv v0.13.7

**Resultado:** Todas las versiones respondieron correctamente y fueron comprobadas.

### 2. Clonar el repositorio

El README indica clonar el repositorio y entrar en su carpeta.
```bash
git clone https://github.com/FelipeGo18/AgroSense.git
cd AgroSense
```
**Resultado:** Se registra exitosamente la clonación del repositorio actualizado.

### 3. Preparar los archivos `.env`

El README indica crear `.env` y `web/.env` a partir de sus archivos de ejemplo.
```bash
cp .env.example .env
cp web/.env.example web/.env
```
**Resultado:** Se comprueba la creación de los archivos .env a través de los ejemplos dentro de los directorios especificados `AgroSense` y `AgroSense/web`

### 4. Levantar la base de datos y la API

El README indica levantar la base de datos y la API, teniendo Docker Desktop abierto, y utilizando el siguiente comando:

```bash
docker compose up --build app
```

**Resultado:** la imagen `agrosense-app` se construyó correctamente. El contenedor de PostgreSQL no pudo enlazar `127.0.0.1:5432` porque Windows/Docker informó que el acceso al socket no estaba permitido. La base no llegó a estar saludable y la API no arrancó.

**Siguiente intento:** cambiar `POSTGRES_PORT` en `.env` a un puerto local disponible, por ejemplo `5433` como dice el caso de si un puerto está ocupado en el README, y repetir el comando. Después, comprobar la API con:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

**Resultado de la comprobación de salud:** OK. JSON de respuesta:
```
{
  "status": "ok",
  "accounts": {
    "available": true,
    "reason": "ok",
    "current_migration": "1.3",
    "expected_migration": "1.3"
  }
}
```
### 5. Levantar la web

El README indica abrir otra terminal y ejecutar:

```bash
npm --prefix web install      # solo la primera vez, o cuando cambie package.json
npm --prefix web run dev
```

**Resultado:** OK. Se levanta correctamente la página web en **`http://localhost:5173`**

## Sin Docker

Este recorrido requiere PostgreSQL 17 instalado y configurado localmente, además de `uv` y las herramientas `psql` y `pg_dump` disponibles en `PATH`. La prueba actual se realiza en una máquina aparte a la prueba con Docker.

### 1. Requisitos y PostgreSQL
- Tener git instalado (https://git-scm.com/). Se prueba con git v2.55.0
- Instalar PostgreSQL 17 (https://www.postgresql.org/download/). Se prueba con PostgreSQL v17.11
- Instalar node.js (https://nodejs.org/) en una versión igual o superior a la 22. Se prueba con node v26.13.0
- Instalar uv (https://docs.astral.sh/uv/) en una versión igual o superior a la 0.13. Se prueba con uv v0.13.7

**Resultado:** Se verifica la instalación y se comprueba la presencia de psql en PATH con `psql --version`. Se verifica pg_dump con `pg_dump --version`.

### 2. Clonar el repositorio y preparar los archivos `.env`

El README indica clonar el repositorio desde git. Se usan los mismos pasos que el setup con Docker.

```bash
git clone https://github.com/FelipeGo18/AgroSense.git
cd AgroSense
```

Además, indica crear `.env` y `web/.env` a partir de sus archivos de ejemplo.
```bash
cp .env.example .env
cp web/.env.example web/.env
```
**Resultado:** Se comprueba la creación de los archivos .env a través de los ejemplos dentro de los directorios especificados `AgroSense` y `AgroSense/web`

### 3. Crear el usuario y la base de datos

El README indica crear el usuario y la base local con los valores definidos en `.env`.

```bash
psql -U postgres -c "create user agrosense with password 'la-clave-de-su-env' createdb"
psql -U postgres -c "create database agrosense owner agrosense"
```

**Resultado:** Se edita el campo POSTGRES_PASSWORD en el `.env` con una contraseña para el usuario local. Además, se añade POSTGRES_HOST y se verifica de nuevo el puerto. En este caso, el puerto por defecto 5432 funciona para esta máquina.

### 4. Instalar dependencias y preparar la base

Comandos indicados en el README:

```bash
uv sync
uv run python -m backend.db.migrate
```

**Resultado:** El comando `uv run python -m backend.db.migrate` arroja que la base de datos no responde. Se verifica estado de la base de datos en primera instancia.

**Siguiente intento:** Se reinicia el estado de Visual Studio Code para terminar la instancia de la terminal e iniciar un estado cero. La base de datos se encuentra al día. Estado: OK.

### 5. Levantar la API y la web

Comandos indicados en el README:

```bash
uv run uvicorn backend.api.main:app --reload --port 8000 --no-access-log
npm --prefix web install      # solo la primera vez, o cuando cambie package.json
npm --prefix web run dev
```

**Resultado:** OK. Los servicios de frontend y backend se ejecutan correctamente. Se prueban escenarios transaccionales para verificar el vínculo con la base de datos local desde la funcionalidad de crear cuenta. Los servicios responden correctamente y la base de datos responde peticiones.

## Conclusión

Se logran ambos escenarios con y sin Docker de manera exitosa, haciendo ajustes pertinentes en máquinas diferentes con versiones similares. Se marca el primer criterio de aceptación de la HU-021 como verificado.

# Estructura del repositorio

La estructura del repositorio se encuentra en tres documentos. Una estructura resumen está en `README.md`, una estructura más detallada está en `CLAUDE.md` y la organización de subsistemas con responsabilidades (fuera de estructura real de carpetas) está en `specs/03-sistemas.md`.

- **Criterios de aceptación:**
  - [X] README de arranque probado por otra persona. Escrito el 12 de octubre de 2026 (`README.md`, «Cómo correr el proyecto», con Docker y sin Docker); falta que lo pruebe otra persona en una máquina limpia
  - [X] Estructura del repositorio acordada
