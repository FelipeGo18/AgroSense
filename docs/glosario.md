# Glosario

Términos que aparecen en las specs, explicados en lenguaje sencillo.

## Metodología

| Término | Qué significa |
|---|---|
| Épica (EP) | Un bloque grande de trabajo con un objetivo claro, como «armar los datos de clima». Agrupa historias de usuario. |
| Historia de usuario (HU) | Una tarea pequeña escrita como «Como [quién], quiero [qué], para [por qué]». Dice quién se beneficia y para qué sirve. Se termina en horas. |
| Criterio de aceptación | Una condición que se puede comprobar con sí o no para dar la HU por terminada. |
| P0 / P1 | P0 es lo obligatorio para la demo. P1 es lo deseable, solo si sobra tiempo. |
| S / M / L | Tamaño estimado de una HU: S ≈ 2 h, M ≈ 4 h, L ≈ 8 h de una persona. |
| Fase 0 | Trabajo previo al hackatón (10 de octubre al 13 de noviembre). |
| Hito | Punto de control. Hito 1 (horas 16–20): un diagnóstico real visible en la URL pública. Hito 2 (horas 26–34): todo el P0 pasa las pruebas y se congela el alcance. |
| Spec | Documento que describe qué se construye. El código sigue a la spec. |

## Arquitectura

| Término | Qué significa |
|---|---|
| Monolito modular | Un solo programa de backend, ordenado por dentro en módulos con responsabilidades separadas. |
| Motor | El módulo que aplica las reglas y decide el semáforo y el ranking. No sabe nada de la web. |
| API | La capa que recibe las peticiones de la web, llama al motor y devuelve la respuesta. No toma decisiones. |
| Endpoint | Una «dirección» de la API a la que la web le pide algo. Por ejemplo, `/diagnostics`. |
| Contrato | El acuerdo escrito sobre el formato exacto de las tablas y de las respuestas de la API. |
| OpenAPI | El archivo que describe todos los endpoints, lo que piden y lo que responden. |
| Mock / respuestas simuladas | Respuestas falsas con el formato real, para que la web avance antes de que exista la API. En este proyecto se hacen con MSW. |
| Pipeline | El proceso que, antes de la demo, descarga y limpia los datos y calcula los indicadores. |
| Parquet | Formato de archivo binario para tablas: pesa poco, se lee rápido y conserva los tipos de dato. Se abre con Polars o DuckDB, no con un editor de texto. |
| JSON | Formato de texto para respuestas con estructura anidada. Es lo que viaja entre la API y la web. |
| Polars | Biblioteca de Python para manejar tablas de datos. |
| DuckDB | Base de datos analítica que lee Parquet con SQL. Aquí es opcional y solo para explorar. |
| Manifiesto (`manifest.json`) | Archivo que dice con qué versión de datos y reglas se produjo un resultado, y qué cobertura tiene. |
| Lint / CI | Revisiones automáticas del código cada vez que alguien sube un cambio. |

## Frontend

| Término | Qué significa |
|---|---|
| Low-poly | Estilo 3D con pocas caras y facetas visibles, sin texturas realistas. Es liviano de dibujar. |
| three.js / React Three Fiber | Biblioteca para dibujar 3D en el navegador, y su versión para usarla con componentes de React. |
| GSAP | Biblioteca de animación web. ScrollTrigger ata animaciones al scroll. |
| glTF | Formato liviano para modelos 3D en la web. |
| Modo ligero | Versión 2D de la app, con la misma información, para celulares sencillos o con poca señal. |
| Storyboard | Tabla toma por toma de una animación, escrita antes de construirla. |
| Token de diseño | Valor con nombre (un color, un tamaño, una duración) que comparten Figma y el código. |
| CC0 | Licencia que permite usar y modificar un recurso sin restricciones. |

## Datos y dominio

| Término | Qué significa |
|---|---|
| EVA | Evaluaciones Agropecuarias Municipales: área sembrada y producción por municipio y semestre. |
| UPRA | Unidad de Planificación Rural Agropecuaria. |
| SIPSA | Sistema de información de precios y abastecimiento del sector agropecuario (DANE). |
| DIVIPOLA | Código oficial de cada municipio (5 dígitos). Es la única llave territorial. |
| NASA POWER | Servicio de la NASA con datos diarios de clima por punto (lluvia, temperatura). |
| Anomalía | Cuánto se aleja un valor de lo normal. Una anomalía de lluvia de −18 % significa que llovió 18 % menos de lo habitual. |
| Normal | El promedio histórico de referencia para un periodo. |
| ET0 | Evapotranspiración de referencia: cuánta agua pierde el suelo por evaporación y por las plantas en un día de referencia. Se calcula con Hargreaves (FAO-56). |
| Kc | Coeficiente de cultivo: factor que ajusta la ET0 según la etapa del cultivo. Una planta recién sembrada gasta menos agua que una adulta. |
| Déficit de agua | ET0 × Kc menos lluvia efectiva. Es lo que falta por aportar con riego. |
| NDVI | Índice de satélite que indica qué tan verde y sana está la vegetación. (P1) |
| Semáforo | Verde, amarillo, rojo o no evaluable para una ventana de siembra. |
| Señal | Cada una de las tres evaluaciones que alimentan el semáforo: clima, oferta, mercado. |
| Sobreoferta | Cuando se siembra tanto de un cultivo en una zona que puede saturar el mercado. |
| Rotación | Secuencia de cultivos en el mismo lote a lo largo del tiempo. |
| Ventana de siembra | Un semestre (A o B) para un cultivo en un municipio. |
| Semestre A / B | A es enero–junio; B es julio–diciembre (supuesto por confirmar en HU-001). |
