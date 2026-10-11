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
| Storyboard | Tabla toma por toma de una animación, escrita antes de construirla. |
| Token de diseño | Valor con nombre (un color, un tamaño, una duración) que comparten Figma y el código. |
| CC0 | Licencia que permite usar y modificar un recurso sin restricciones. |
| Modo simulación | Modo de desarrollo, activado con una variable de entorno, que usa datos y usuarios de ejemplo y permite forzar cada caso. |
| Ambiente en vivo | Día, noche, lluvia y viento aproximados de ahora en la escena. No cambia ningún resultado. |
| Modo ligero | Versión 2D de la app, con la misma información, para celulares sencillos o con poca señal. |

## Cuentas

| Término | Qué significa |
|---|---|
| Lote | Un terreno del agricultor en un municipio, dibujado en el mapa o con el área escrita. Puede tener varios cultivos a la vez, cada uno en una parte de su área. Un usuario con cuenta puede tener varios lotes, en varias zonas. |
| Parte del lote | El área que ocupa un cultivo dentro de un lote. Se mide en hectáreas y no se dibuja. La parte sin sembrar es la parte libre. |
| Zona | El municipio donde está un lote. |
| Temporada | Un ciclo de un cultivo en una parte de un lote: qué se sembró, en cuánta área, qué había antes en ese terreno, cuándo se sembró y cuándo se cosechó. |
| Historial del terreno | Las relaciones entre temporadas de un mismo lote. Como el agricultor divide y junta partes como quiere, no es una cadena sino una red: una temporada puede venir de varias anteriores (`follows_season_ids`) y tener varias sucesoras. El área de una temporada no pasa de la suma de las áreas de las que viene más el área libre del lote, y la suma de las temporadas en curso nunca pasa del área del lote. Es el historial que usan las rotaciones y el progreso. Antes se llamaba «cadena de temporadas» y guardaba una sola anterior (`follows_season_id`, cambiado el 11 de octubre de 2026). |
| Dividir y juntar partes | Dividir: al cosechar, repartir ese terreno entre varios cultivos (una temporada con varias sucesoras). Juntar: sembrar un cultivo en el terreno de varias temporadas cosechadas (una temporada que viene de varias). |
| Progreso | Lo que se deriva del historial de un lote: temporadas registradas, rotaciones que cumplen las reglas (por cada relación entre una temporada y una sucesora, con las reglas que viola, `violated_rule_ids`) e hitos. |
| Restaurar | Recuperar un lote o una temporada borrados hace menos de 30 días. El historial muestra lo borrado con el botón «Restaurar»; después de 30 días se borra para siempre. |
| Finca temporal | La finca de quien usa la app sin cuenta: área y porcentaje por cultivo. Se envía solo para calcular y no se guarda en el servidor. En el P0 vive solo durante la visita; guardarla en el navegador es HU-149 (P1). |
| Consentimiento | La aceptación del usuario de que se guarden sus datos, con la versión del texto que aceptó. La vigente es la versión 3, que suma si el lote tiene riego, las prioridades guardadas en el perfil y el uso de sus siembras en totales anónimos. |
| Sesión | El tiempo en que un usuario queda conectado tras iniciar sesión. Vive en una cookie y en la tabla `sessions`; vence a los 30 días. |
| Argon2 | Método para guardar contraseñas como un resumen irreversible: la contraseña nunca se guarda tal cual. |

## Datos y dominio

| Término | Qué significa |
|---|---|
| Región piloto | La región con la que se prepara el P0: hoy, una región de Colombia. Es un supuesto mientras el reto no confirme región y datos (enunciado del 28 de octubre, HU-002). Lo propio de un país vive en los adaptadores de cada fuente, no en el modelo. |
| EVA | Evaluaciones Agropecuarias Municipales: área sembrada y producción por municipio y semestre. Es el único dato del proyecto que va por semestre. Es de Colombia (región piloto). |
| FAOSTAT | Base de datos estadísticos de la FAO (producción y área por país y año). Candidata, por confirmar, como fuente de contraste de la oferta; no es un dato municipal. |
| FAO EcoCrop | Base de datos de la FAO con los rangos óptimos y los límites absolutos de temperatura, lluvia y otros factores para muchas especies. Candidata, por confirmar, para las curvas de calificación de las fichas. |
| Fuente de contraste | Una fuente de un indicador que no es la que calcula la señal, pero se muestra al lado para comparar (por ejemplo, las siembras registradas en AgroSense junto a EVA). Nunca se mezcla ni se promedia con la otra. `sources.yaml` dice qué fuente calcula cada señal en cada región. |
| Siembras registradas en AgroSense | Totales por municipio y cultivo de las temporadas en curso de los usuarios con cuenta. Fuente de contraste de la oferta (P1). Nunca se muestran con menos de 5 cuentas ni dato por usuario. |
| UPRA | Unidad de Planificación Rural Agropecuaria. |
| SIPSA | Sistema de información de precios y abastecimiento del sector agropecuario (DANE). |
| DIVIPOLA | Código oficial de cada municipio de Colombia (5 dígitos). Es la llave territorial de la región piloto: la regla general es usar el código oficial de la unidad territorial de la región (R7). |
| NASA POWER | Servicio de la NASA con datos diarios de clima por punto (lluvia, temperatura). |
| Anomalía | Cuánto se aleja un valor de lo normal. Por ejemplo, la variación del área sembrada frente al promedio de años anteriores. |
| Normal | El promedio histórico de referencia para un periodo. |
| ET0 | Evapotranspiración de referencia: cuánta agua pierde el suelo por evaporación y por las plantas en un día de referencia. Se calcula con Hargreaves (FAO-56). |
| Kc | Coeficiente de cultivo: factor que ajusta la ET0 según la etapa del cultivo. Una planta recién sembrada gasta menos agua que una adulta. |
| Déficit de agua | ET0 × Kc menos lluvia efectiva. Es lo que falta por aportar con riego. |
| Balance hídrico | La cuenta de cuánta agua necesita un cultivo en cada etapa frente a la lluvia que suele caer. Sirve para el plan de agua y para la señal de agua. |
| NDVI | Índice de satélite que indica qué tan verde y sana está la vegetación. (P1) |
| Ventana de siembra | Una fecha de siembra más lo que dura ese cultivo en campo, de la siembra a la cosecha estimada. Es la unidad de toda la decisión. Las ventanas se comparan por mes de siembra y, dentro de un mes, por semana. |
| Aptitud | Si un cultivo se puede dar en un municipio. Se decide solo con la altitud del municipio frente al rango absoluto de la ficha del cultivo. Es un filtro previo, no una señal: un cultivo que no es apto no se evalúa por ventanas (por ejemplo, papa en la costa). Trae una nota informativa de 0 a 100 (`suitability.score`) con la curva de altitud (100 dentro del rango óptimo, 0 fuera del absoluto), que no entra al semáforo ni al orden. Valores: `suitable`, `not_suitable`, `insufficient_data`. |
| Semáforo | Verde, amarillo, rojo o no evaluable para una ventana de siembra. |
| Señal | Cada una de las evaluaciones independientes de una ventana que alimentan el semáforo. En el P0 son seis: agua, heladas, calor, suelo, oferta y mercado. En el P1 se suman exceso de lluvia, enfermedades por clima y clima de cosecha. Cada una se mide contra lo que ese cultivo necesita o aguanta. |
| Señal de agua (`water`) | Dice si la lluvia que suele caer en la ventana cubre lo que el cultivo necesita en cada etapa, según cuánta agua retiene el suelo por su textura (un suelo arenoso se seca antes que uno arcilloso). Con riego, la falta de lluvia no es un riesgo: la señal informa cuánto riego haría falta. |
| Textura del suelo | La proporción de arena, limo y arcilla. Cambia cuánta agua guarda el suelo entre lluvias, por eso entra en la señal de agua; no entra en la señal de suelo. |
| Señal de calor (`heat`) | Dice si en la ventana suelen darse temperaturas máximas por encima de lo que el cultivo aguanta, según su ficha (`heat_max_c`). |
| Calificación (`score`) | Número de 0 a 100 que recibe cada señal con una curva por cultivo, al estilo EcoCrop de la FAO: 100 dentro del rango óptimo del cultivo, 0 fuera de sus límites absolutos y una recta entre ambos. El nivel sale de la calificación: 70 a 100 favorable, 40 a 69 moderado, 0 a 39 desfavorable (cortes en `thresholds.yaml`). |
| Señal crítica | Una señal cuya calificación baja del umbral crítico. Cuando cuenta, basta para un semáforo rojo. El suelo nunca es crítico; el agua solo lo es sin riego. |
| Riesgo grave de clima | Agua, heladas o calor críticos; en el P1, también el exceso de lluvia (`excess_rain`) crítico. Cuenta siempre para la luz, aunque el agricultor le ponga peso 0 a esa señal. |
| Alto riesgo (`high_risk`) | Una ventana con alguna señal que cuenta desfavorable y crítica. Va siempre después de las demás y nunca entra entre las mejores, por alto que sea su balance. |
| Factor limitante (`limiting_signal`) | La señal con la calificación más baja entre las que cuentan. Por la «ley del mínimo», una ventana vale lo que vale su peor factor: es lo primero que ordena las ventanas. |
| Peso o prioridad | Qué tanto le importa cada señal al agricultor, de 0 a 5. AgroSense propone un peso por defecto para cada una (`weights.yaml`) y el agricultor lo cambia. Peso 0: la señal se ve, pero no cambia la luz (salvo un riesgo grave de clima). Peso 4 o 5: un resultado moderado cuenta como desfavorable. En las rotaciones hay otras cuatro prioridades: agua, suelo, ingreso y riesgo. |
| Pesos por defecto | Los pesos que propone AgroSense, con quién los definió y por qué (HU-198). Son un criterio del equipo, no un dato agronómico. |
| Señal que cuenta (`counts`) | Una señal con peso mayor que 0, o un riesgo grave de clima. Solo las que cuentan cambian la luz y el factor limitante. |
| Luz por defecto y luz con sus prioridades | La luz con los pesos de AgroSense (`overall_default`) y la luz con los pesos del agricultor (`overall`). Si difieren, se muestran las dos: «Con el criterio de AgroSense: amarillo · Con sus prioridades: verde». Decide el agricultor. |
| Balance de la ventana (`weighted_score`) | Número de 0 a 100: el promedio de las calificaciones de sus señales, ponderado por los pesos. En el contrato es el campo `weighted_score`. Ordena las ventanas cuyo factor limitante cae en la misma decena. No decide el semáforo ni compensa un factor muy malo o un alto riesgo. |
| Mejores ventanas (`best_windows`) | Hasta tres ventanas de los próximos doce meses, las primeras del orden (factor limitante y luego balance) que no son de alto riesgo. Puede no haber ninguna. Es historia de la zona, no un pronóstico. |
| Otra ventana (`other_window`) | Acción sugerida cuando lo que sale mal es el clima de esa fecha: conviene buscar otra fecha de siembra. Si lo que sale mal es el suelo, la oferta o el mercado, o el cultivo no es apto, la acción es rotar. |
| Alternativas (`alternatives`) | Con la acción rotar: hasta tres cultivos aptos para la zona que en esa misma ventana salen bien en clima y tienen mejor oferta, con su razón. Es una sugerencia; decide el agricultor. |
| Riego (`irrigated`) | Si el lote tiene riego. Lo dice el agricultor. Cambia cómo se lee la señal de agua. |
| Helada | Una noche en que la temperatura mínima a 2 m baja de 2 °C (criterio de amenaza de la UPRA con datos del IDEAM). Cerca del suelo hace más frío y la planta se daña. |
| Calendario del cultivo | Un cultivo en un municipio a lo largo del año. Tiene dos lecturas: «Mi cultivo», para lo ya sembrado (mes a mes, la etapa, las heladas y el calor a vigilar y el riego probable, de la siembra a la cosecha estimada), y «Planear una siembra» (las ventanas de los próximos doce meses, por mes y por semana, ordenadas por su factor limitante y, entre parecidas, por su balance). |
| Etapa sensible | Etapa del cultivo en la que una helada o el calor le hacen daño, según su ficha. |
| Vigile | Aviso del calendario cuando un mes tiene riesgo de helada o de calor y el cultivo está en una etapa sensible (`frost.watch`, `heat.watch`). |
| Cosecha estimada | Fecha en que se espera la cosecha si el clima se comporta como un año normal. No es un pronóstico. |
| Año normal | El clima promedio del histórico de la zona, día por día. Se usa para estimar lo que viene después del último dato real. |
| Lote vivo | La vista de un lote como diorama: cada cultivo en su etapa, con el clima de ahora y una línea de tiempo que se puede mover. |
| Finca de bloques | El ambiente alrededor del lote vivo (casa, cerca, huerta, árbol y perro). Es decoración: no muestra ningún dato. |
| SoilGrids | Mapa mundial de propiedades del suelo de ISRIC, con celdas de 250 m. Es una estimación, con su rango de incertidumbre. |
| pH | Qué tan ácido o alcalino es el suelo. Cada cultivo tolera un rango. |
| Carbono orgánico | La materia orgánica del suelo. Si es baja, conviene rotar con abonos verdes, descanso o leguminosas. |
| Abono verde | Un cultivo que no se cosecha: se incorpora al suelo para devolverle materia orgánica y nitrógeno. |
| Corrección por altitud | Ajuste de la temperatura de NASA POWER, que viene de una celda de unos 50 km, a la altura real del municipio. |
| Sobreoferta | Cuando se siembra tanto de un cultivo en una zona que puede saturar el mercado. |
| Rotación | Secuencia de cultivos en el mismo terreno de un lote a lo largo del tiempo. Si el terreno se dividió o se juntó, sus cultivos anteriores son los de todas las temporadas de las que viene. |
| Semestre A / B (solo en EVA) | Así publica EVA la oferta: A es enero–junio; B es julio–diciembre (supuesto por confirmar en HU-001). La decisión no se evalúa por semestre: la señal de oferta lee el semestre en que cae la fecha de siembra, y la respuesta lo dice. |
