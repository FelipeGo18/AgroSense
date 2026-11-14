# Impacto de AgroSense: potencial y límites

HU-133. Este texto alimenta la descripción de la entrega (HU-132) y el cierre del guion de la demo (HU-131).

**Todo lo que sigue es impacto potencial, no garantizado.** AgroSense apoya decisiones con la historia de la zona y con reglas con fuente; no promete cosechas, ingresos ni una mejora medida del suelo. La decisión final es siempre del agricultor.

## El contexto

- **El suelo ya está en riesgo.** El 40 % del territorio de Colombia presenta algún grado de degradación de los suelos por erosión, según la línea base del IDEAM a escala 1:100.000 ([Ministerio de Ambiente, 2016](https://www.minambiente.gov.co/40-del-territorio-colombiano-presenta-algun-grado-de-degradacion-de-suelos-por-erosion/)).
- **La región piloto pesa.** Cundinamarca (36 %) y Boyacá (27 %) producen cerca del 63 % de la papa del país, y más de 100.000 productores se dedican a ese cultivo, según Fedepapa ([Agronegocios, mayo de 2023](https://www.agronegocios.co/agricultura/cundinamarca-boyaca-narino-y-antioquia-representan-90-de-la-produccion-de-papa-3611353)). Para que los patógenos no se acumulen en el suelo, la FAO dice que no se siembra papa en el mismo terreno año tras año, sino en rotaciones de tres años o más («rotations of three or more years», FAO, 2008).
- **Los datos existen, pero dispersos.** La NASA publica clima, lluvia, relieve, verdor y humedad del suelo para casi todo el planeta, pero no en una forma que un agricultor pueda usar para decidir qué sembrar después.

AgroSense cubre los **239 municipios de Boyacá y Cundinamarca** y **7 cultivos del altiplano** (papa, arveja, haba, maíz, zanahoria, cebolla de bulbo y avena con vicia como abono verde), más el descanso.

## Impacto ambiental

La tabla dice lo que hace el diseño del MVP. Qué está funcionando el día de la entrega lo dice su descripción (HU-132). Las fuentes de las reglas, con su enlace y la página citada, están en `catalog/rotation_rules.yaml` y `catalog/crops.yaml`.

| Qué hace AgroSense | Por qué puede ayudar | Cómo se sabe |
|---|---|---|
| Propone rotaciones de hasta 3 ciclos. Descarta las que siembran seguido la misma familia o papa después de papa, y califica peor las que vuelven a la papa antes de tiempo | Cortar el ciclo de las plagas y los patógenos que se quedan en el suelo | Reglas con fuente: rotar familias (Penn State Extension) y no sembrar papa después de papa (ICA, punta morada) descartan. Cuánto esperar para volver a la papa es criterio del equipo, apoyado en las «rotations of three or more years» de la FAO (2008) |
| Prefiere las estrategias con leguminosas (arveja, haba y la vicia de la avena con vicia) | Las leguminosas fijan nitrógeno del aire, una ventaja económica y sostenible para la agricultura | Que fijan nitrógeno: FAO, informe final del Año Internacional de las Legumbres (2019). Que es una ventaja para la finca: [Foyer et al. (2016), *Nature Plants*](https://eprints.whiterose.ac.uk/id/eprint/102468/). AgroSense no dice cuánto nitrógeno queda: compara estrategias |
| Prefiere abonos verdes y descanso cuando el carbono orgánico del suelo es bajo | Aportar materia orgánica al suelo, a largo plazo | Carbono de SoilGrids y el corte de materia orgánica baja de los suelos paperos del altiplano (CEVIPAPA). Ojo: en un ensayo de Corpoica en el altiplano, con abono verde antes y después de la papa, no hubo un aumento importante de la materia orgánica en 18 meses (Murcia, en CEVIPAPA). Por eso no se promete un cambio rápido |
| Cuenta cuántos meses queda el suelo descubierto y lo cruza con la pendiente | Menos suelo desnudo en ladera es menos erosión | Pendiente de NASADEM y el 12 % de pendiente desde el que, según el IGAC, aumenta la susceptibilidad del suelo a la erosión |
| Calcula cuánta agua necesita cada ciclo y en qué meses no alcanza la lluvia | Regar solo cuando y cuanto hace falta | Lluvia de GPM IMERG (con la de NASA POWER para contrastar) y la ET0 de NASA POWER por FAO-56 |

## Impacto social

- **Datos de la NASA al alcance de un pequeño productor**, en palabras sencillas: cada resultado dice por qué, con qué dato y de qué fuente.
- **Desde el celular, con datos móviles caros:** el modo ligero no descarga las animaciones y la web funciona desde 320 px de ancho.
- **Sin cuenta:** se puede consultar con solo el municipio y el área. Con cuenta, los lotes y su historial se guardan con consentimiento, y el agricultor puede borrarlo todo (R9).
- **La decisión es del agricultor:** él pone sus prioridades (cuánto le importa el agua, las heladas o el precio), y cuando su criterio y el de AgroSense dan otra luz, se muestran las dos.

## Impacto económico

- **Menos pérdidas por clima:** el diagnóstico muestra en qué épocas han helado o hecho calor en las etapas sensibles del cultivo, y cuáles ventanas de siembra salen mejor en la historia de la zona.
- **Menos insumos:** las leguminosas fijan su propio nitrógeno del aire, una ventaja económica para la finca (ver la tabla de impacto ambiental). AgroSense no calcula cuánto fertilizante se ahorra.
- **La oferta y el precio, como valor agregado:** la oferta (EVA) y el mercado (precios mayoristas de SIPSA) entran al diagnóstico y al criterio de ingreso de las estrategias. Hoy salen «datos insuficientes»: ninguna fuente dice qué es «mucho sembrado» o «precio bajo», y AgroSense no usa un criterio propio para eso (decisión 12). En las estrategias nunca excluyen una opción: solo bajan su criterio de ingreso.
- **No promete ingresos.** No predice cuánto se va a cosechar ni a qué precio se va a vender.

## Cómo se mediría (propuesta, después del reto)

Nada de esto está medido todavía. Para saber si el impacto es real, haría falta:

1. **Uso:** cuántas consultas hay por municipio y cultivo, con el contador anónimo previsto (HU-170, sin datos de quién consulta).
2. **Decisiones:** con agricultores que acepten participar, cuántos eligen una estrategia con leguminosa o abono verde que no hacían antes.
3. **Suelo:** análisis de suelo del lote al principio y después de una rotación completa, comparados con lotes de la misma zona que no cambiaron.
4. **Validación:** que un agrónomo de la región revise las reglas que hoy son «criterio del equipo».

## Límites

- **No es un pronóstico.** El diagnóstico, el orden de las ventanas y «Qué cambió» son historia de la zona: dicen cómo le ha ido a cada época, no cómo será el próximo año.
- **La salud del suelo es una comparación, no una predicción.** No hay modelo de suelo: AgroSense compara estrategias por reglas y no dice cuánto va a mejorar el suelo.
- **Varias reglas son criterio del equipo.** Los cortes de nitrógeno, carbono, cobertura, erosión y espera de la papa (por ciclos, porcentaje y meses) son del equipo, apoyados en fuentes que no dan esos números exactos. Se rotulan así y falta que un agrónomo los valide.
- **Los datos son de la zona, no del lote.** El clima de NASA POWER es de una celda de unos 50 km, el suelo de SoilGrids es un mapa global de 250 m y la humedad del suelo y el verdor son de la zona. El agua del plan es una estimación: hay que verificar la humedad del suelo en campo y hacer un análisis de suelo del lote (R10).
- **NASA POWER es un reanálisis**, no una observación directa. En el altiplano ve menos heladas de las que mide el IDEAM. Y las dos fuentes de lluvia de la NASA, GPM IMERG y POWER, dan casi el doble de lluvia que las 259 estaciones del IDEAM en los valles. Por eso el agua se califica con la lluvia del año seco y las heladas llevan un aviso.
- **Sin datos no hay señal.** Si falta una fuente, la señal sale como «datos insuficientes» y no cambia el semáforo: no se rellena con otra cosa (R1).
- **Es un MVP de hackatón.** No todas las partes del motor están terminadas a la vez: lo que todavía no se calcula sale como «datos insuficientes» o como «no disponible», nunca con un resultado inventado. La descripción de la entrega (HU-132) dice qué se ve funcionando.
- **Es una región piloto.** Las reglas y los cultivos son del altiplano de Boyacá y Cundinamarca. Llevarlo a otra región pide sus propios cultivos, fuentes y validación.
- **No sustituye la asistencia técnica agropecuaria.**
