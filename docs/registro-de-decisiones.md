# Registro de decisiones

Las decisiones de arquitectura se explican en `decisiones.md`. Aquí se registran las decisiones puntuales con su fecha. Para cambiar una, se edita su fila y los documentos que la reflejan.

## Tomadas

| Decisión | Elegida | Fecha |
|---|---|---|
| Herramienta de backlog | GitHub Projects | 10 oct 2026 |
| Framework de la API | FastAPI (Axum descartado, ver `specs/04-stack.md`) | 10 oct 2026 |
| Cuentas y regla R9 | Cuentas con lotes y temporadas; R9 reescrita (decisión 6) | 10 oct 2026 |
| Clima en vivo | Ambiente de la escena, nunca insumo de la decisión (decisión 7) | 10 oct 2026 |
| Responsable del contrato | Haider: cambia `specs/02-contratos.md` o aprueba cada cambio | 10 oct 2026 |
| Base de datos | PostgreSQL propio en Docker, sin servicios gestionados (Supabase descartado) | 10 oct 2026 |
| Inicio de sesión | Autenticación propia: usuario y contraseña (Argon2), sesión en cookie; recuperar la contraseña en P1 | 10 oct 2026 |
| Condiciones actuales | Open-Meteo, solo el «ahora», sin pronóstico | 10 oct 2026 |
| Dónde se prepara el frontend | Fase 0 en este repositorio (`web/`, EP-15); la app de la demo, en un repositorio nuevo durante el evento | 10 oct 2026 |
| Estilo | Inspiración de estilo en *The Farmer Was Replaced* y la web de GTA VI, sin copiar sus elementos (`specs/05-frontend.md`) | 10 oct 2026 |
| Inicio | Mascota satélite; habla de AgroSense, no del problema ni de NASA | 10 oct 2026 |
| Navegación | Una experiencia continua con URL por nivel y por lote; quien vuelve con sesión entra directo a Mi finca | 10 oct 2026 |
| Paleta y semáforo | Paleta del moodboard más un rojo (#B83A2B); variantes oscuras para texto; botón principal en oliva oscuro con texto blanco; tonos claros siempre con texto noche (HU-152, `design/tokens/tokens.json`) | 10 oct 2026 |
| Tipografía | Fredoka 600 para títulos y Atkinson Hyperlegible para texto, 18 px corriente y 14 px mínimo (HU-152) | 10 oct 2026 |
| Variables de Figma | No se crean: los tokens viven en `design/tokens/tokens.json` y en Figma como frame de muestras con nombre (Tokens Studio es de pago) | 10 oct 2026 |
| Lenguaje visual de los componentes | Diorama low-poly: esquinas biseladas, caras trianguladas y canto en lugar de sombra; nada con esquinas redondas. Descartados «instrumento de campo» y «cuaderno de campo» (HU-153) | 10 oct 2026 |
| Orden de trabajo del frontend | Cada pieza se diseña y aprueba primero en Figma; el código va después | 10 oct 2026 |
| Control de prioridad | Cinco semillas y un «0» que se tocan, en lugar de un deslizador (se retira Radix Slider) | 10 oct 2026 |
| Rotaciones y finca | Se unen en Mi finca, por lote | 10 oct 2026 |
| Audio | P1 (HU-157) | 10 oct 2026 |
| «Acerca de» | Sin sección aparte: el panel «¿Cómo funciona y de dónde sale esto?» cubre fuentes, versión y cómo se decide | 10 oct 2026 |
| Skills de frontend | `greensock/gsap-skills` y `anthemflynn/ccmp` (react-three-fiber), leídas antes de instalarlas | 10 oct 2026 |

## Dependen de una verificación

No se deciden por preferencia: se resuelven con el resultado de la HU indicada y se pasan a la tabla anterior.

| Tema | Se resuelve con | Fecha límite | Rol |
|---|---|---|---|
| Tamaño del equipo | Confirmación de los integrantes | 17 oct | Todos |
| Fuente del clima histórico | HU-002 (enunciado del 28 de octubre) | 30 oct | Datos |
| Región piloto | HU-001 (cobertura de EVA) | 31 oct | Producto y Datos |
| SIPSA en el P0 | HU-003 | 1 nov | Datos |
| Qué código preparado se puede llevar al evento | HU-004 (términos de Space Apps 2026) | 2 nov | Producto |
