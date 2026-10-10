# Sistemas y subsistemas

Cuatro sistemas de producto más un sistema de soporte. Las cuentas (M8) y las condiciones actuales (M9) viven en el backend, fuera del motor. Los escenarios (M5) son una función del motor y la API es su capa de entrega, por eso no son sistemas aparte. La columna «No debe» marca dónde termina cada responsabilidad.

Los códigos (D1, AG1, M1, W1, S1…) se usan en las épicas y en las HUs.


### Datos · pipeline offline

| Código | Subsistema | Responsabilidad | Entrega | No debe |
|---|---|---|---|---|
| D1 | Ingesta | Un adaptador por fuente (NASA, EVA, SIPSA, límites DANE) que descarga y guarda la copia cruda con fuente, fecha y periodo | Archivos crudos en caché y registro en la tabla de fuentes | Mezclar fuentes ni calcular indicadores |
| D2 | Validación y normalización | Revisar columnas, tipos, rangos, duplicados y cobertura; asignar DIVIPOLA, semestre y unidades comunes | Tablas limpias, filas rechazadas y reporte de calidad | Rellenar huecos sin marcarlos |
| D3 | Indicadores | Calcular anomalía y tendencia de lluvia, evapotranspiración de referencia mensual, variación de área sembrada e índice estacional de precio | Tablas por granularidad según el contrato | Decidir el semáforo ni aplicar umbrales |
| D4 | Publicación | Escribir Parquet y el manifiesto con versión, cobertura y fuentes | Dataset versionado que lee la API | Recalcularse cuando el usuario consulta |


### Catálogo agronómico · datos en el repositorio

| Código | Subsistema | Responsabilidad | Entrega | No debe |
|---|---|---|---|---|
| AG1 | Fichas de cultivo | Familia, ciclo, semestres de siembra, necesidad de agua, raíz, fijación de nitrógeno, rango de altitud, y etapas con su coeficiente de cultivo (Kc) | Archivo de cultivos validado contra su esquema | Recomendar cultivos |
| AG2 | Reglas de rotación | Declarar reglas como datos: tipo (filtro, bonificación o penalización), condición, efecto y criterio | Archivo de reglas versionado | Generar secuencias; eso lo hace el motor (M3) |
| AG3 | Evidencia | Registrar la fuente de cada campo y regla, con sus límites de uso | Entradas en la tabla de fuentes | Aceptar reglas sin fuente |


### Motor de decisión y API · un backend, módulos separados

| Código | Subsistema | Responsabilidad | Entrega | No debe |
|---|---|---|---|---|
| M1 | Señales | Evaluar clima, oferta y mercado de una ventana con umbrales de configuración | Por señal: estado, nivel, indicadores usados y razones | Dar nivel a una señal sin datos |
| M2 | Agregador del semáforo | Combinar señales con reglas explícitas y elegir una acción | Luz global, acción y limitaciones | Promediar señales |
| M3 | Rotaciones | Generar secuencias, filtrarlas con AG2 y puntuarlas según las prioridades | Ranking con desglose por criterio y motivos de exclusión | Puntuar secuencias inválidas |
| M4 | Explicaciones | Convertir señales, reglas y puntajes en razones con plantillas fijas | Texto en español ligado a indicadores y reglas | Mencionar causas no evaluadas |
| M5 | Escenarios P1 | Aplicar un cambio en memoria a los indicadores y reejecutar M1 a M3 | Resultado del escenario y diferencias con el caso base | Modificar el dataset ni presentarse como pronóstico |
| M6 | API | Validar entradas, llamar al motor, serializar y responder errores uniformes | Endpoints del contrato OpenAPI | Contener lógica de decisión |
| M7 | Balance hídrico | Calcular la necesidad de agua de cada cultivo por etapa (ET0 × Kc menos lluvia efectiva) y el volumen según su área en la finca | Déficit mensual y volumen por cultivo y por finca, en año normal y seco | Presentarse como medición del lote ni guardar datos de la finca |
| M8 | Cuentas y lotes | Registrar e iniciar sesión (contraseña con Argon2 y sesión en cookie), guardar usuarios, lotes y temporadas en PostgreSQL, pedir al motor el progreso de un lote y borrar la cuenta a pedido | Endpoints de cuenta del contrato | Vivir dentro del motor (R6), guardar datos sin consentimiento ni pedir datos que no se usan (R9) |
| M9 | Condiciones actuales | Consultar a Open-Meteo la condición aproximada de ahora en el municipio, con caché de 15 minutos | Lluvia, nubes, viento y temperatura actuales con fuente y hora | Alimentar al motor, cambiar un resultado o mostrar pronóstico (decisión 7) |


### Aplicación web · React

| Código | Subsistema | Responsabilidad | Entrega | No debe |
|---|---|---|---|---|
| W1 | Contexto | Elegir municipio, cultivo y semestre entre opciones del catálogo | Consulta válida | Permitir combinaciones fuera del catálogo |
| W2 | Diagnóstico | Mostrar semáforo, señales, razones, acción y limitaciones | Vista de diagnóstico | Usar solo color para el estado |
| W3 | Indicadores | Gráficas de lluvia frente a lo normal y de área sembrada, con unidades y periodo | Gráficas de tendencia | Mezclar unidades en un mismo eje |
| W4 | Rotaciones | Prioridades del usuario y ranking con desglose y razones | Vista de recomendación | Ocultar por qué se excluyó una opción |
| W5 | Escenarios P1 | Controles de escenario y comparación con el caso base | Vista comparativa | Presentar el escenario como predicción |
| W6 | Estados | Carga, vacío, sin cobertura, error y datos de ejemplo | Componentes comunes | Mostrar datos ficticios sin rotularlos |
| W7 | Mi finca | Con cuenta: los lotes del usuario por zona y, por lote, estado actual, próxima siembra, qué sembrar después, plan de agua e historial. Sin cuenta: una finca temporal en el dispositivo con su plan de agua | Vista de finca, calendario de agua y progreso | Enviar datos a guardar sin cuenta (R9) |
| W8 | Inicio y mascota | Presentar qué es AgroSense con la mascota satélite y llevar a consultar sin cuenta o a entrar | Pantalla de inicio y personaje animado | Prometer más de lo que la app hace |
| W9 | Cuenta y sesión | Registro, inicio y cierre de sesión con usuario y contraseña, consentimiento, perfil, preferencias y borrado de la cuenta | Vistas de cuenta | Pedir datos que no se usan |


### Soporte · transversal

| Código | Subsistema | Responsabilidad | Entrega | No debe |
|---|---|---|---|---|
| S1 | Repositorio y CI | Estructura, convenciones, lint y pruebas en cada cambio | Repositorio que arranca en menos de 10 minutos | Bloquear el avance con reglas excesivas |
| S2 | Despliegue | Un contenedor con API y web en una URL pública | Demo accesible por enlace | Depender de un único servicio sin respaldo |
| S3 | Calidad y trazabilidad | Casos de prueba de referencia, manifiesto y reproducción del dataset con un comando | Pruebas que pasan y versión trazable | Esperar al final para probar |
| S4 | Entrega | Guion, video, descripción del proyecto y envío | Entrega completa para el jurado | Prometer más de lo que la demo muestra |
| S5 | Modo simulación | Con una variable de entorno, servir datos y usuarios simulados y un panel para forzar escenarios, estados y tiempo | Entorno para ver y probar cada caso sin backend real | Activarse en producción o mostrar datos simulados sin rótulo (R5) |
