# Orden de desarrollo de las épicas

El orden lo marcan las dependencias: primero lo que desbloquea a los demás, luego lo que puede avanzar en paralelo y al final lo que integra.

Las etapas de este documento ordenan el trabajo. No confundir con la **fase 0**, que es el periodo previo al evento (ver `docs/glosario.md`).

## Etapa 0: cimientos (fase 0 y hora 0, nadie avanza sin esto)

| Orden | Épica | Por qué va primero |
|---|---|---|
| 1 | EP-00 Alcance piloto | Define cultivos, región y periodos de datos. Sin esto no se sabe qué datos bajar ni qué catálogo armar. |
| 2 | EP-01 Contratos y datos de ejemplo | Congela el esquema de datos y el OpenAPI y deja datos y respuestas de ejemplo. Habilita el paralelismo. |
| 3 | EP-02 Base desplegada | Repositorio, CI y un despliegue vacío que ya funcione. Así se integra desde el principio. |

EP-00 y EP-01 son las más importantes: un error en el contrato afecta a todos los demás.

En paralelo, durante la fase 0, **EP-15 Identidad visual y prototipo del frontend**, el diseño de la mascota (HU-171) y el modo simulación (HU-014) adelantan el estilo, las animaciones, los assets y un prototipo navegable en este repositorio, contra datos de ejemplo. No bloquean ni dependen de las demás épicas.

## Etapa 1: en paralelo, cada quien sobre el contrato

| Frente | Épicas | Trabaja con |
|---|---|---|
| Datos | EP-03 Oferta EVA, EP-04 Clima NASA (con altitud, lluvia mensual HU-042, heladas y temperatura máxima por mes HU-045 y por semana HU-193), lluvia y ET0 mensuales (HU-143), suelo de EP-18 (HU-181) | Datos reales producidos por el pipeline |
| Catálogo | EP-06 Catálogo agronómico y etapas con Kc (HU-142), con los rangos óptimos y absolutos de cada cultivo (HU-199) y los pesos por defecto (HU-198) | Fichas de cultivo con rango de altitud, temperatura, lluvia, pH y heladas, abonos verdes, reglas de rotación y etapas; `weights.yaml` |
| Motor, primero | Balance hídrico con la textura del suelo (HU-144) y etapas de una ventana (HU-150, HU-186). Van antes del diagnóstico: la señal `water` necesita el balance y la duración de la ventana sale de las etapas | Parquet de ejemplo |
| Motor, después | EP-07 Diagnóstico: aptitud (HU-191), calificación con curvas (HU-196), sus seis señales (agua HU-071, heladas HU-077, calor HU-190, suelo HU-183, oferta HU-072 y mercado HU-073), orden de las ventanas por factor limitante (HU-192), semáforo con prioridades y dos luces (HU-074), alternativas (HU-197), endpoint (HU-076) y catálogos (HU-078); luego el endpoint del calendario (HU-179), que reutiliza esas señales | Parquet de ejemplo |
| Web | EP-09 Web diagnóstico (con cultivo no apto y mejores ventanas, HU-194; prioridades, HU-202; dos luces y alternativas, HU-203), inicio (HU-173) | Respuestas simuladas (MSW) |
| Cuentas | Base de datos y autenticación (HU-161 a HU-163, con el consentimiento versión 3) | PostgreSQL en Docker |
| Calidad | EP-12 (HU-121 casos de referencia) | Resultado esperado escrito antes de programar |

Al terminar esta fase el diagnóstico debe funcionar de punta a punta, aunque sea con datos de ejemplo. **Hito 1** (horas 16–20): un diagnóstico real visible en la URL pública.

## Etapa 2: integrar y extender

| Orden | Épica | Nota |
|---|---|---|
| 4 | Cambio de datos de ejemplo a reales | Paso de integración; si el contrato se respetó, encaja. |
| 5 | EP-08 Rotaciones, con el suelo (HU-184) | Necesita el catálogo (EP-06), el motor (EP-07, con la aptitud de HU-191) y el suelo publicado (HU-181). |
| 6 | EP-10 Web rotaciones | Puede empezar con respuestas simuladas en cuanto exista el contrato. |
| 7 | EP-16 Cuentas, lotes y progreso | Lotes, temporadas con partes que se dividen y se juntan, historial con lo borrado y «Restaurar» (HU-204), registro y Mi finca (HU-164 a HU-169); después, el suelo del lote (HU-182) y su vista (HU-185). La regla de áreas al dividir y juntar partes ya está en el contrato (HU-165). |
| 8 | EP-12 Calidad y trazabilidad | Transversal: empieza pequeño en la etapa 1 y se cierra aquí. |

## Etapa 3: cierre

| Orden | Épica | Nota |
|---|---|---|
| 9 | Lo que queda de EP-14: finca (HU-141), calendario de riego y endpoint del plan de agua (HU-145, HU-146) y vista del calendario (HU-180) | El balance hídrico y las etapas ya se hicieron en la etapa 1. Depende del clima real (EP-04) y de las etapas de cada cultivo (EP-06). Es P0 y no se puede recortar sin que se note, salvo el recorte parcial indicado (solo año normal). |
| 10 | Paisaje vivo (HU-174 a HU-176) | Depende de la escena; se puede reducir a día y noche. |
| 11 | EP-13 Demo y entrega | Guion, caso ensayado, video y documentación de fuentes. Reservar tiempo real para ensayar. |

## Fuera del camino crítico (P1)

- **EP-05 Mercado SIPSA** y **EP-11 Escenarios**, solo si sobra tiempo.
- Las fuentes de contraste de la oferta (HU-201) y las siembras registradas en AgroSense (HU-200). HU-201 espera un lugar en el contrato para los valores de contraste que no son municipales, como los de FAOSTAT; HU-200 espera las cuentas (EP-16): el corte diario versionado y el consentimiento versión 3 ya están decididos (`specs/01-reglas.md`).
- Las tres señales del P1 (`excess_rain`, `disease` y `harvest_weather`, HU-195) con sus datos (HU-046), solo si sobra tiempo. Mientras no existan, no aparecen en la respuesta.
- EP-05 tiene un riesgo extra: no está verificado que SIPSA cubra lo necesario. El diagnóstico debe funcionar sin ella, con la señal de mercado como «datos insuficientes».

## Reglas para no atascarse

1. El camino crítico es EP-00 → EP-01 → datos reales → balance hídrico y etapas → diagnóstico integrado → demo. Todo lo demás se recorta antes. La calificación con curvas (HU-196) necesita los rangos de las fichas (HU-199), cuyas columnas ya están en `crops` (`specs/02-contratos.md`): falta llenarlas con fuente en la fase 0.
2. Orden de recorte si hay retraso en la hora 34: ver `docs/plan-48h.md`.
3. No empezar ninguna épica de la etapa 1 hasta que Haider o Felipe den por congelado el contrato de EP-01.
