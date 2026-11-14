# Licencias de AgroSense y de lo que usa

Documentación de las licencias de terceros que piden los términos de NASA Space Apps 2026 (HU-230; <https://www.spaceappschallenge.org/legal/>): el contenido original debe ser libre o tener una licencia aprobada por la OSI, y la NASA no acepta una solución sin la licencia de cada material de terceros.

## El código de AgroSense

Apache 2.0 (`LICENSE`, en la raíz del repositorio; aprobado por Felipe el 10 de noviembre de 2026).

## Lo que hay que saber

- **GSAP** (`gsap` y `@gsap/react`, las animaciones de la web) no tiene una licencia de la OSI: usa la «Standard no-charge license» de GreenSock (<https://gsap.com/standard-license>), gratis para todo uso, también el comercial. Es su permiso documentado. Solo se carga con movimiento: en modo ligero no se descarga (HU-158), y la web funciona igual sin él.
- **psycopg** (el conector de PostgreSQL) es LGPL-3.0, una licencia de la OSI; AgroSense lo usa como librería, sin modificarlo.
- **Las tipografías** (Atkinson Hyperlegible y Fredoka, por `@fontsource`) son OFL-1.1, una licencia de la OSI.
- **Los datos** no son software: cada fuente dice abajo con qué condición se usa. Todas permiten usarlas citándolas. Las fichas de la UPRA permiten la «reproducción parcial sin fines comerciales con cita»: AgroSense solo toma sus rangos de temperatura media, con la cita, y no es comercial.
- **Lo que sale de DIVIPOLA del DANE** (CC BY-SA 4.0), como la tabla `municipalities`, se publica con esa misma licencia.

## Datos y fuentes (tabla `sources` del dataset publicado)

Cada dato y cada regla agronómica apunta a una de estas fuentes (R8). La licencia es la que dice cada fuente; sin licencia explícita, se usa con cita, como pide la fuente.

| Fuente | Institución | Licencia o condición de uso |
|---|---|---|
| `agrosense_diseno` · Catálogo visual de AgroSense (design/finca/cultivos.py) | Equipo RealE4Life | Del proyecto |
| `alharbi_2021_faba` · Alharbi et al. (2021): Evaluation of Frost Damage and Pod Set in Faba Bean (Vicia faba L.) under Field Conditions. Plants 10(9):1925 | MDPI, Plants; doi:10.3390/plants10091925 | Acceso abierto (CC BY 4.0 por confirmar) |
| `barrales_2002` · Barrales Domínguez et al. (2002): Relaciones térmicas en el sistema suelo-planta-atmósfera durante la incidencia de una helada. Revista Fitotecnia Mexicana 25(3):289-297 | Sociedad Mexicana de Fitogenética; Universidad Autónoma Chapingo | Acceso abierto (Redalyc); licencia por confirmar |
| `cenicafe_lapse_rate` · Regionalización de la temperatura del aire en Colombia (Chaves Córdoba y Jaramillo Robledo, 1999), tabla 3 | Centro Nacional de Investigaciones de Café (Cenicafé) | Artículo de acceso abierto con derechos de autor reservados: se usan dos cifras (el gradiente térmico) con su cita |
| `ciren_1989_chacras` · CIREN-CORFO: Requerimientos de clima y suelo. Chacras y hortalizas, publicación n.º 85 (1989) | Centro de Información de Recursos Naturales (CIREN), Chile | Sin dato; se cita |
| `dane_divipola` · DIVIPOLA- Códigos municipios | Departamento Administrativo Nacional de Estadística (DANE) | Creative Commons Attribution \| Share Alike 4.0 International |
| `dane_mgn_2025` · Marco Geoestadístico Nacional 2025 · Municipios | Departamento Administrativo Nacional de Estadística (DANE) | Datos abiertos del DANE, con cita de la fuente (por confirmar en HU-122) |
| `dane_sipsa` · SIPSA · Precios mayoristas diarios (servicio web) | Departamento Administrativo Nacional de Estadística (DANE) | Términos y condiciones del DANE (https://www.dane.gov.co/index.php/terminos-y-condiciones): se autoriza el uso, aprovechamiento, transformación y análisis de la información citando «Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co». Se rigen por la ley colombiana y el DANE puede cambiarlos sin aviso. |
| `fairlie_ortega_1995` · Fairlie y Ortega (1995): Efecto de la presencia de heladas simuladas en diferentes estados fenológicos de la papa cv. Ccompis. Revista Latinoamericana de la Papa 7/8:86-93 | Asociación Latinoamericana de la Papa (ALAP); PISA/INIAA, Puno | Acceso abierto; licencia por confirmar |
| `fao_56` · FAO-56: Crop evapotranspiration (Allen, Pereira, Raes y Smith, 1998). Tablas 11 y 12 | FAO | Publicación de la FAO, uso con cita |
| `fao_66` · FAO-66: Crop yield response to water (Steduto, Hsiao, Fereres y Raes, 2012). Sección 3.4, papa, pp. 185-186 | FAO, Irrigation and Drainage Paper 66 | Publicación de la FAO, uso con cita |
| `fao_crop_info_potato` · FAO Land & Water: Crop Information, Potato | FAO, Land and Water Division | Publicación de la FAO, uso con cita |
| `fao_ecocrop` · FAO EcoCrop · fichas de datos por especie | Organización de las Naciones Unidas para la Alimentación y la Agricultura (FAO) | CC BY 4.0 (catálogo de datos de la FAO) |
| `fao_frost_2005` · FAO: Frost protection: fundamentals, practice and economics, vol. 1 (Snyder y de Melo-Abreu, 2005). Cap. 4, tabla 4.5; cap. 5 | FAO, Environment and Natural Resources Series 10 | Publicación de la FAO, uso con cita |
| `fao_iyp_2019` · FAO: The International Year of Pulses, final report (2019) | FAO | Publicación de la FAO, uso con cita |
| `fao_soils_bulletin_55` · FAO Soils Bulletin 55: Guidelines, land evaluation for irrigated agriculture (1985), formato 5 | FAO | Publicación de la FAO, uso con cita |
| `fews_net_wrsi` · FEWS NET · Water Requirement Satisfaction Index (WRSI) y sus clases | Famine Early Warning Systems Network (FEWS NET) y USGS; clases publicadas por el Banco Mundial | Información pública del USGS; las clases, del catálogo de datos del Banco Mundial (CC BY 4.0) |
| `imerg` · GPM IMERG Final Run V07 · Lluvia mensual por satélite (GPM_3IMERGM) | NASA y JAXA, misión GPM (Global Precipitation Measurement); distribuido por GES DISC de la NASA | Datos abiertos de la NASA (política de datos de ESDS): sin restricciones de uso, con cita (https://disc.gsfc.nasa.gov/data-guidelines) |
| `mapa_zarc_2025` · Zoneamento Agrícola de Risco Climático (ZARC): Portaria SPA/MAPA n.º 388, del 21 de agosto de 2025 | Ministério da Agricultura e Pecuária (MAPA), Brasil | Acto oficial del gobierno de Brasil, publicado en el Diário Oficial |
| `msu_e1307_onion` · Zandstra, Grafius, Lacy y Warncke: Commercial Vegetable Recommendations: Onions, MSU E1307 (revisión de 1996) | Michigan State University Extension | Sin dato; se cita |
| `msu_e1437_carrot` · Zandstra y Baker: Commercial Vegetable Recommendations: Carrots, MSU Extension Bulletin E-1437 (1980) | Michigan State University Extension | Sin dato; se cita |
| `nasa_power` · NASA POWER · Datos diarios por punto (comunidad AG) | NASA Langley Research Center, proyecto POWER (Prediction Of Worldwide Energy Resources) | La página de POWER no da una licencia; pide citar la fuente (https://power.larc.nasa.gov/docs/referencing/) |
| `nasadem` · NASADEM HGT v001: modelo de elevación de 1 segundo de arco (unos 30 m) | NASA Jet Propulsion Laboratory (JPL); distribuido por el LP DAAC de la NASA y el USGS | Datos abiertos de la NASA (política de datos de ESDS): sin restricciones de uso, con cita |
| `ndsu_a1166_pea` · NDSU Extension: Field Pea Production, A1166 (revisión de diciembre de 2021) | North Dakota State University Extension | Sin dato; se cita |
| `purdue_corn07` · Nielsen, R. L.: Drought and Heat Stress Effects on Corn Pollination (Corny News, Purdue, sin fecha) | Purdue University, Agronomy | Sin dato; se cita |
| `saskpulse_stress_2023` · Saskatchewan Pulse Growers: Environmental Stresses in Pulses (mayo de 2023) | Saskatchewan Pulse Growers | Sin dato; se cita |
| `senamhi_atlas_heladas_2010` · SENAMHI y FAO: Atlas de heladas del Perú (2010). Tablas 2.2 y 2.3 | Servicio Nacional de Meteorología e Hidrología del Perú (SENAMHI) y FAO | Publicación pública, sin licencia explícita; se cita |
| `ucanr_7226_carrot` · Nuñez, Hartz, Suslow et al.: Carrot Production in California, UC ANR Publication 7226 (2008) | University of California, Agriculture and Natural Resources; doi:10.3733/ucanr.7226 | Sin dato; se cita |
| `unlu_horticultura` · Universidad Nacional de Luján: Producción Vegetal III (Horticultura), fichas de cebolla, arveja y zanahoria (sin año) | Universidad Nacional de Luján (UNLu), Argentina | Sin dato; se cita |
| `upra_cebolla_bulbo` · UPRA: Cultivo comercial de cebolla de bulbo, identificación de zonas aptas en Colombia, escala 1:100.000 | Unidad de Planificación Rural Agropecuaria (UPRA), Ministerio de Agricultura | Propiedad de la UPRA; reproducción parcial sin fines comerciales con cita |
| `upra_papa_diacol` · UPRA: Cultivo de papa Diacol Capiro para uso industrial, identificación de zonas aptas en Colombia, escala 1:100.000 | Unidad de Planificación Rural Agropecuaria (UPRA), Ministerio de Agricultura | Propiedad de la UPRA; reproducción parcial sin fines comerciales con cita |

## Librerías de Python (51, de `uv.lock`)

| Paquete | Versión | Licencia |
|---|---|---|
| alembic | 1.20.0 | MIT |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| argon2-cffi | 25.1.0 | MIT |
| argon2-cffi-bindings | 26.1.0 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| cffi | 2.1.1 | MIT-0 |
| click | 8.5.0 | BSD-3-Clause |
| colorama | 0.4.6 | BSD |
| et-xmlfile | 2.0.0 | MIT |
| fastapi | 0.143.0 | MIT |
| h11 | 0.16.0 | MIT |
| httpcore | 1.0.9 | BSD-3-Clause |
| httptools | 0.9.0 | MIT |
| httpx | 0.28.1 | BSD |
| idna | 3.20 | BSD-3-Clause |
| iniconfig | 2.3.1 | MIT |
| mako | 1.4.3 | MIT |
| markupsafe | 3.0.4 | BSD-3-Clause |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| openpyxl | 3.1.5 | MIT |
| opentelemetry-api | 1.45.1 | Apache-2.0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pluggy | 1.6.0 | MIT |
| polars | 2.0.0 | MIT |
| polars-runtime-32 | 2.0.0 | MIT |
| psycopg | 3.3.6 | LGPL-3.0-only |
| psycopg-binary | 3.3.6 | LGPL-3.0-only |
| pycparser | 3.11 | BSD-3-Clause |
| pydantic | 2.14.1 | MIT |
| pydantic-core | 2.50.1 | MIT |
| pydantic-settings | 2.15.0 | MIT |
| pygments | 2.21.0 | BSD-2-Clause |
| pyproj | 3.8.0 | MIT |
| pytest | 9.1.1 | MIT |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| pyyaml | 6.0.3 | MIT |
| ruff | 0.17.0 | MIT |
| shapely | 2.2.0 | BSD-3-Clause |
| sqlalchemy | 2.1.4 | MIT |
| starlette | 1.7.0 | BSD-3-Clause |
| structlog | 26.1.0 | MIT OR Apache-2.0 |
| tifffile | 2026.10.15 | BSD-3-Clause |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |
| tzdata | 2026.5 | Apache-2.0 |
| uvicorn | 0.54.0 | BSD-3-Clause |
| uvloop | 0.23.0 | MIT OR Apache-2.0 |
| watchfiles | 1.3.0 | MIT |
| websockets | 17.2 | BSD-3-Clause |

## Librerías de la web que van en la aplicación (69, de `web/package-lock.json`)

| Paquete | Versión | Licencia |
|---|---|---|
| @fontsource/atkinson-hyperlegible | 5.3.0 | OFL-1.1 |
| @fontsource/fredoka | 5.3.0 | OFL-1.1 |
| @gsap/react | 2.1.2 | SEE LICENSE AT https://gsap.com/standard-license |
| @mapbox/jsonlint-lines-primitives | 2.0.3 | MIT |
| @mapbox/point-geometry | 1.1.0 | ISC |
| @mapbox/tiny-sdf | 2.3.0 | BSD-2-Clause |
| @mapbox/unitbezier | 1.0.0 | BSD-2-Clause |
| @mapbox/vector-tile | 3.0.0 | BSD-3-Clause |
| @maplibre/geojson-vt | 6.2.0 | ISC |
| @maplibre/maplibre-gl-style-spec | 26.4.4 | ISC |
| @maplibre/mlt | 1.3.0 | (MIT OR Apache-2.0) |
| @maplibre/vt-pbf | 4.3.2 | MIT |
| @radix-ui/primitive | 1.2.0 | MIT |
| @radix-ui/react-compose-refs | 1.1.5 | MIT |
| @radix-ui/react-context | 1.3.0 | MIT |
| @radix-ui/react-dialog | 1.3.0 | MIT |
| @radix-ui/react-dismissable-layer | 1.2.0 | MIT |
| @radix-ui/react-focus-guards | 1.2.0 | MIT |
| @radix-ui/react-focus-scope | 1.3.0 | MIT |
| @radix-ui/react-id | 1.1.4 | MIT |
| @radix-ui/react-portal | 1.2.0 | MIT |
| @radix-ui/react-presence | 1.1.11 | MIT |
| @radix-ui/react-primitive | 2.2.0 | MIT |
| @radix-ui/react-slot | 1.5.0 | MIT |
| @radix-ui/react-use-callback-ref | 1.1.5 | MIT |
| @radix-ui/react-use-controllable-state | 1.3.0 | MIT |
| @radix-ui/react-use-effect-event | 0.0.5 | MIT |
| @radix-ui/react-use-layout-effect | 1.1.4 | MIT |
| @remix-run/route-pattern | 0.22.1 | MIT |
| @tanstack/query-core | 5.104.2 | MIT |
| @tanstack/react-query | 5.104.2 | MIT |
| @types/geojson | 7946.0.16 | MIT |
| @types/react | 19.3.0 | MIT |
| @types/react-dom | 19.3.0 | MIT |
| aria-hidden | 1.2.6 | MIT |
| bidi-js | 1.1.0 | MIT |
| cookie-es | 3.1.1 | MIT |
| csstype | 3.2.3 | MIT |
| detect-node-es | 1.1.0 | MIT |
| earcut | 3.2.4 | ISC |
| get-nonce | 1.0.1 | MIT |
| gl-matrix | 3.4.4 | MIT |
| gsap | 3.15.0 | Standard 'no charge' license: https://gsap.com/standard-license. |
| json-stringify-pretty-compact | 4.0.0 | MIT |
| kdbush | 4.1.0 | ISC |
| lenis | 1.3.26 | MIT |
| maplibre-gl | 6.11.2 | BSD-3-Clause |
| minimist | 1.2.8 | MIT |
| murmurhash-js | 1.0.0 | MIT |
| pbf | 5.1.2 | BSD-3-Clause |
| potpack | 2.1.0 | ISC |
| protocol-buffers-schema | 3.6.1 | MIT |
| quickselect | 3.0.0 | ISC |
| react | 19.3.0 | MIT |
| react-dom | 19.3.0 | MIT |
| react-remove-scroll | 2.7.2 | MIT |
| react-remove-scroll-bar | 2.3.8 | MIT |
| react-router | 8.4.0 | MIT |
| react-style-singleton | 2.2.3 | MIT |
| require-from-string | 2.0.2 | MIT |
| resolve-protobuf-schema | 2.1.0 | MIT |
| scheduler | 0.28.0 | MIT |
| terra-draw | 1.35.0 | MIT |
| terra-draw-maplibre-gl-adapter | 1.4.1 | MIT |
| tinyqueue | 3.0.0 | ISC |
| tslib | 2.8.1 | 0BSD |
| use-callback-ref | 1.3.3 | MIT |
| use-sidecar | 1.1.3 | MIT |
| world-atlas | 2.0.2 | ISC |

## Herramientas de desarrollo de la web (514 paquetes; no van en la aplicación)

Solo se usan para construir y probar la web (Vite, TypeScript, Vitest, ESLint, Playwright…). Por licencia:

| Licencia | Paquetes |
|---|---|
| MIT | 353 |
| Apache-2.0 | 76 |
| ISC | 29 |
| MPL-2.0 | 25 |
| BSD-2-Clause | 13 |
| BSD-3-Clause | 9 |
| MIT-0 | 2 |
| BlueOak-1.0.0 | 2 |
| (MIT OR CC0-1.0) | 2 |
| CC-BY-4.0 | 1 |
| CC0-1.0 | 1 |
| ? | 1 |

Se regenera con los paquetes de `uv.lock`, `web/package-lock.json` y `data/published/sources.parquet` (14 de noviembre de 2026).
