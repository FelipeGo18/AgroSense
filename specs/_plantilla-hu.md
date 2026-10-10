# Plantilla de historia de usuario (HU)

Copia este bloque dentro del archivo de su épica (`specs/epicas/EP-XX-*.md`) y reemplaza los campos. Una HU se termina en horas; si es mayor que L (≈ 8 h), divídela.

```markdown
### HU-XXX · Título corto (máximo 8 palabras)

- **Historia:** Como [agricultor | jurado | motor | desarrollador web | equipo], quiero [qué], para [por qué].
- **Prioridad:** P0 | P1 · **Tamaño:** S | M | L · **Estado:** pendiente
- **Criterios de aceptación:**
  - [ ] Criterio comprobable 1 (alguien puede decir sí o no sin interpretar)
  - [ ] Criterio comprobable 2
  - [ ] Criterio de borde (sin datos, entrada inválida, límite) cuando aplique
- **Reglas que aplican:** R# (ver `specs/01-reglas.md`)
- **Contrato que toca:** tablas o endpoints de `specs/02-contratos.md`, si aplica
- **Notas:** supuestos por confirmar, dependencias entre HUs, enlaces a fuentes
```

## Lista de verificación antes de aceptar una HU

- [ ] El «quién» es una persona o un componente real.
- [ ] Cada criterio se puede verificar con sí o no.
- [ ] Hay al menos un criterio de borde cuando aplica.
- [ ] No viola ninguna regla R1–R10.
- [ ] Los identificadores coinciden con el contrato.
- [ ] No mezcla capas (web, motor, datos).
- [ ] Tiene tamaño y prioridad.
- [ ] Está reflejada en `specs/BACKLOG.md`.

## Tamaños

| Tamaño | Esfuerzo de una persona |
|---|---|
| S | ≈ 2 h |
| M | ≈ 4 h |
| L | ≈ 8 h |

## Estados

`pendiente` → `en curso` → `en revisión` → `hecha`. Una HU solo pasa a `hecha` cuando todos sus criterios están marcados y la revisión (ver agente `calidad`) la aprobó.
