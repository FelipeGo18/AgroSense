# Riesgos

| Riesgo | Efecto | Mitigación |
|---|---|---|
| Los términos de 2026 o el evento local limitan lo preparado antes | La fase 0 solo puede incluir investigación y diseño | HU-004; plan válido en ambos casos, con capacidad recalculada |
| El enunciado del 28 de octubre exige datasets NASA distintos de POWER | Hay que rehacer la ingesta del clima | Adaptadores por fuente (D1); HU-002 antes de construir |
| EVA no trae DIVIPOLA o usa otra definición de semestre | Las uniones fallan o mezclan periodos | Verificar en HU-001; tabla de correspondencia documentada |
| SIPSA no cubre la región o los cultivos | La propuesta de valor sobre el precio se debilita | La señal sale como datos insuficientes y la demo lo dice; EP-05 queda en P1 |
| Reglas agronómicas sin respaldo | El jurado cuestiona las recomendaciones | R8: sin fuente no hay regla; revisión cruzada en HU-061 |
| El P0 no cabe en 48 horas | Producto incompleto al cierre | Equipo de 5 o más, hitos en las horas 20 y 34, orden de recorte |
| Falla la red o el alojamiento durante la demo | No se puede mostrar en vivo | Video de respaldo y ejecución local con Docker |
| Pocos datos: EVA desde 2019, dos semestres por año | Tendencias poco robustas | Hablar de señales e historial, no de predicción; marcar calidad `partial` |
| El plan de riego se toma como una instrucción exacta | Riego excesivo o insuficiente en el lote | R10: rangos en lugar de valores únicos, rótulo de estimación y recomendación de verificar la humedad en campo |
| La ET0 por Hargreaves es menos precisa que Penman-Monteith | Necesidades de agua sobre o subestimadas | Documentarlo; pasar a Penman-Monteith en P1 si POWER entrega radiación, humedad y viento para la zona (por confirmar) |
| Muchos pequeños productores no tienen riego | El calendario de riego no les sirve tal cual | El mismo déficit se presenta como riesgo de estrés hídrico, que sirve para elegir cultivo o fecha de siembra |
