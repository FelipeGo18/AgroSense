# Orden de desarrollo de las épicas

El orden lo marcan las dependencias: primero lo que desbloquea a los demás, luego lo que puede avanzar en paralelo y al final lo que integra.

## Fase 0: cimientos (hora 0, nadie avanza sin esto)

| Orden | Épica | Por qué va primero |
|---|---|---|
| 1 | EP-00 Alcance piloto | Define cultivos, región y semestres. Sin esto no se sabe qué datos bajar ni qué catálogo armar. |
| 2 | EP-01 Contratos y datos de ejemplo | Congela el esquema de datos y el OpenAPI y deja datos y respuestas de ejemplo. Habilita el paralelismo. |
| 3 | EP-02 Base desplegada | Repositorio, CI y un despliegue vacío que ya funcione. Así se integra desde el principio. |

EP-00 y EP-01 son las más importantes: un error en el contrato afecta a todos los demás.

## Fase 1: en paralelo, cada quien sobre el contrato

| Frente | Épicas | Trabaja con |
|---|---|---|
| Datos | EP-03 Oferta EVA, EP-04 Clima NASA | Datos reales producidos por el pipeline |
| Catálogo | EP-06 Catálogo agronómico | Fichas de cultivo, reglas de rotación y etapas |
| Motor | EP-07 Diagnóstico | Parquet de ejemplo |
| Web | EP-09 Web diagnóstico | Respuestas simuladas (MSW) |
| Calidad | EP-12 (HU-121 casos de referencia) | Resultado esperado escrito antes de programar |

Al terminar esta fase el diagnóstico debe funcionar de punta a punta, aunque sea con datos de ejemplo. **Hito 1** (horas 16–20): un diagnóstico real visible en la URL pública.

## Fase 2: integrar y extender

| Orden | Épica | Nota |
|---|---|---|
| 4 | Cambio de datos de ejemplo a reales | Paso de integración; si el contrato se respetó, encaja. |
| 5 | EP-08 Rotaciones | Necesita el catálogo (EP-06) y el motor (EP-07). |
| 6 | EP-10 Web rotaciones | Puede empezar con respuestas simuladas en cuanto exista el contrato. |
| 7 | EP-12 Calidad y trazabilidad | Transversal: empieza pequeño en la fase 1 y se cierra aquí. |

## Fase 3: cierre

| Orden | Épica | Nota |
|---|---|---|
| 8 | EP-14 Finca y plan de agua | Depende del clima real (EP-04) y de las etapas de cada cultivo (EP-06). Es P0 y no se puede recortar sin que se note, salvo el recorte parcial indicado (solo año normal). |
| 9 | EP-13 Demo y entrega | Guion, caso ensayado, video y documentación de fuentes. Reservar tiempo real para ensayar. |

## Fuera del camino crítico (P1)

- **EP-05 Mercado SIPSA** y **EP-11 Escenarios**, solo si sobra tiempo.
- EP-05 tiene un riesgo extra: no está verificado que SIPSA cubra lo necesario. El diagnóstico debe funcionar sin ella, con la señal de mercado como «datos insuficientes».

## Reglas para no atascarse

1. El camino crítico es EP-00 → EP-01 → datos reales → diagnóstico integrado → demo. Todo lo demás se recorta antes.
2. Orden de recorte si hay retraso en la hora 34: todo el P1; HU-093 con una sola gráfica; plan de agua solo con año normal; explicaciones con una razón por opción; pruebas de CI a mano.
3. No empezar ninguna épica de la fase 1 hasta que el contrato de EP-01 esté acordado por todo el equipo.
