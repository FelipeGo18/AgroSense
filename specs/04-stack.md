# Stack tecnológico

El criterio fue un solo lenguaje en el backend, contratos que generan tipos automáticamente y el menor número de servicios desplegados. **Hay que fijar versiones exactas al crear el repositorio.**

| Capa | Decisión | Por qué | Alternativa descartada |
|---|---|---|---|
| Lenguaje backend | Python 3.12 y `uv` para entornos | Pipeline, motor y API comparten modelos y lenguaje; `uv` da un lockfile reproducible | Axum en Rust: obliga a duplicar los modelos entre Rust y Python |
| Datos tabulares | Polars | Elegido por el equipo; API lazy y Parquet nativo. Con una región el volumen es pequeño, así que la ganancia es de ergonomía más que de necesidad | pandas: también serviría a este volumen |
| Clima NASA (P0) | NASA POWER por punto, comunidad AG, series diarias por centroide municipal | Entrega precipitación y temperatura diarias por punto sin procesar mallas. Con la temperatura máxima y mínima se calcula la ET0 por Hargreaves (FAO-56) | Mallas IMERG en el P0: más trabajo de geoprocesamiento |
| Geodatos | GeoPandas y Shapely; xarray y rioxarray solo en P1 | Centroides y GeoJSON simplificado de la región; las mallas solo hacen falta para SMAP y NDVI | — |
| Almacenamiento | Parquet y `manifest.json`; la API carga en memoria con Polars | El dataset de una región cabe en memoria; un solo formato para todo | DuckDB en la API: se deja solo para explorar en notebooks |
| Motor | Python puro; umbrales y pesos en YAML versionado | Se prueba sin servidor y cambia reglas sin tocar código | — |
| API | FastAPI y Pydantic v2 | Genera el OpenAPI desde los modelos, y de ahí salen los tipos del frontend | — |
| Pruebas | `pytest`, con `TestClient` de FastAPI | Casos de referencia del motor y del contrato | Pruebas end-to-end con navegador: no hay tiempo |
| Frontend | React, TypeScript y Vite; Tailwind y primitivas de Radix con estilo propio | Stack conocido por el equipo; accesibilidad de Radix con la identidad visual de `05-frontend.md` | shadcn/ui tal cual: aspecto genérico |
| 3D y animación | three.js con React Three Fiber y drei; GSAP (ScrollTrigger, SplitText, Flip) y Lenis; Zustand para el estado de escena | Estética low-poly y navegación narrativa con cámara (ver `05-frontend.md`) | — |
| Audio | Howler.js, apagado por defecto | Ambiente y efectos de interfaz con control | — |
| Datos en la web | TanStack Query, tipos con `openapi-typescript` y MSW para respuestas simuladas | La web trabaja contra el contrato desde la hora 0 | — |
| Gráficas y mapa | SVG propio animado con GSAP; la vista regional (HU-095) va en la escena 3D | Pocas gráficas y control total del estilo; un buscador basta para elegir municipio | Recharts: difícil de adaptar al estilo. MapLibre: solo si la escena 3D no alcanza |
| Calidad de código | Ruff en Python; ESLint, Prettier y Vitest en la web; GitHub Actions | Rápidos y con configuración mínima | — |
| Despliegue | Una imagen Docker: FastAPI sirve la API y el build de la web | Un solo servicio, sin CORS. Alojar en un servicio de contenedores con plan gratuito vigente | Web y API separadas: más piezas que pueden fallar |
| Gestión | GitHub Projects: épicas como etiquetas, historias como issues | Vive junto al código | Jira, si el equipo ya lo usa |
