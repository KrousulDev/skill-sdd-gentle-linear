# PHASE-2-BUSINESS-CASES.md

## Objetivo

Definir los **casos de negocio** y el **paso a paso de validación** para la Fase 2 de `sdd-linear`, enfocada en runtime adapters para **Linear** y **Engram**.

Este documento también deja explícito el estado actual real del proyecto para evitar confusión entre:

- lo que ya está implementado
- lo que ya se puede probar hoy
- y lo que todavía falta para integrarlo de verdad con tu cuenta de Linear

---

## Estado actual real de la Fase 2

### Ya implementado

- runtime mode configurable:
  - `stub`
  - `live`
- preflight evaluator
- runtime ports
- stub adapter
- live adapter module/factory segura
- normalized outcomes
- partial success / reconciliation flows
- wrappers OpenCode con `runtimeMode`
- live confirmation UX
- tests automáticos de Fase 2

### Todavía NO cableado a tu cuenta real

**Importante:** hoy el modo `live` **no está conectado automáticamente** a tu cuenta real de Linear ni a un runtime real de Engram.

El adapter live actual está preparado para recibir **handlers reales**, pero por defecto no los trae configurados.

Eso significa:

- podés validar el diseño runtime
- podés validar la política `stub/live`
- podés validar preflight y outcomes
- podés validar reconciliación
- **pero todavía no podés afirmar que ya crea/comenta/cierra issues reales en tu workspace de Linear sin agregar wiring real**

En otras palabras:

> Fase 2 ya construyó el **puente**.
> Pero todavía no conectó ese puente a tu **cuenta real** de Linear/Engram.

---

## Cómo se está integrando Engram con Linear en la arquitectura

La integración está pensada así:

1. **Core neutral**
   - sigue siendo dueño del workflow
   - persiste metadata local
   - decide gates, retries, reconciliation y outcomes

2. **Ports**
   - definen contratos para sistemas externos
   - el core llama interfaces, no vendor SDKs directos

3. **Adapters runtime**
   - `stub`: simula comportamiento
   - `live`: ejecuta side effects reales cuando haya handlers reales

4. **OpenCode wrappers**
   - seleccionan `runtimeMode`
   - validan confirmación live
   - delegan al core

### Modelo esperado de integración real

Cuando el wiring real exista, el flujo de un derived issue debería verse así:

1. El operador detecta un hallazgo.
2. Se registra en **Engram**.
3. Se intenta crear/actualizar el issue en **Linear**.
4. Se persisten ambos outcomes en metadata local.
5. Si uno sale bien y el otro falla, queda un estado de:
   - `reconciliation-required`

Eso ya está modelado a nivel arquitectura/runtime. Lo que falta es el cable real contra tus cuentas/credenciales.

---

## Casos de negocio de Fase 2

## Caso 1 — Sincronización real de estado a Linear

### Objetivo

Cuando un change cambia de estado SDD, el sistema debe poder:

- mapearlo a estado Linear
- despachar la actualización por adapter runtime
- persistir outcome normalizado

### Valor de negocio

- Product/PM ve avance operativo real
- se reduce drift entre estado local y estado externo

### Estado actual

- **stub:** sí
- **live real contra tu cuenta:** todavía no

---

## Caso 2 — Derived issue con Engram + Linear y reconciliación

### Objetivo

Cuando se descubre trabajo emergente:

- debe quedar trazado en Engram
- debe intentarse su proyección a Linear
- si un sistema falla, debe quedar reconciliación pendiente

### Valor de negocio

- evita pérdida de contexto
- evita duplicación de issues
- permite recuperación operativa si un sistema falla y el otro no

### Estado actual

- **stub:** sí
- **live real contra tu cuenta:** todavía no

---

## Caso 3 — Archive con live gating seguro

### Objetivo

Cuando el archive pasa gates locales:

- se debe poder intentar comentario/cierre vía adapter runtime
- respetando smoke policy y confirmación live

### Valor de negocio

- evita cierres prematuros
- permite un futuro close/comment real sobre Linear

### Estado actual

- contract + runtime model: sí
- smoke-policy: sí
- live real en tu workspace: todavía no

---

## Caso 4 — Operación segura con `stub` por default

### Objetivo

Todo el sistema debe seguir siendo seguro si alguien no configuró live.

### Valor de negocio

- no rompe desarrollo local
- evita side effects accidentales en Linear
- mantiene portabilidad entre máquinas/proyectos

### Estado actual

- **implementado**

---

## Qué sí podemos probar hoy

Podemos probar de forma honesta:

### 1. Config runtime actual

Verificar que el config tenga:

```json
"runtime": {
  "mode": "stub",
  "allowedModes": ["stub", "live"]
}
```

### 2. Que `stub` siga siendo el default seguro

### 3. Que `live` requiera opt-in explícito

### 4. Que el preflight exista

### 5. Que los wrappers documenten `runtimeMode` y confirmación live

### 6. Que los tests de Phase 2 estén pasando

### 7. Que el sistema modele correctamente:

- partial success
- reconciliation-required
- blocked live outcomes

---

## Qué NO podemos afirmar hoy

No podemos afirmar honestamente todavía que:

- se conecta de verdad a tu cuenta de Linear
- usa credenciales reales tuyas
- crea issues reales en tu workspace
- comenta/cierra issues reales en tu workspace
- guarda observaciones reales en Engram vía adapter live

¿Y por qué?

Porque el adapter live actual está preparado así:

- acepta **handlers**
- normaliza outcomes
- pero no trae por default el wiring real a tus sistemas

Eso es una decisión buena de seguridad, no una falla.

---

## Paso a paso para revisar Fase 2 hoy

## Paso 1 — Verificar config runtime

Abrí:

```text
.ai/workflows/sdd-linear/config.json
```

Confirmá:

- `runtime.mode = stub`
- `allowedModes` incluye `stub` y `live`
- `requireExplicitOptIn = true`
- `smokePolicy.allowClose = false`

---

## Paso 2 — Verificar adapter live actual

Abrí:

```text
.ai/workflows/sdd-linear/runtime/adapters/live.py
```

Qué revisar:

- existe `LiveRuntimeAdapter`
- usa `handlers`
- normaliza outcomes
- falla seguro si la operación live no está configurada

La señal clave está acá:

```python
if handler is None:
    raise RuntimeAdapterError(
        f"Live runtime adapter operation '{operation}' is not configured.",
        code="REMOTE",
        retryable=False,
    )
```

Eso prueba que hoy el modo live **no está conectado por defecto**.

---

## Paso 3 — Verificar wrappers OpenCode

Abrí:

- `.opencode/commands/sdd-linear/sdd-new.md`
- `.opencode/commands/sdd-linear/sdd-status.md`
- `.opencode/commands/sdd-linear/sdd-log-issue.md`
- `.opencode/commands/sdd-linear/sdd-archive.md`

Qué revisar:

- aceptan `runtimeMode`
- documentan `stub|live`
- live requiere frase explícita:
  - `ALLOW_SDD_LINEAR_LIVE`

---

## Paso 4 — Ejecutar la suite de tests de Fase 2

Corré:

```bash
python3 -m unittest discover -s tests
```

Resultado esperado hoy:

- todos los tests en verde
- baseline actual: **31 tests**

---

## Paso 5 — Probar un flujo local con runtime stub

Podés usar cualquier proyecto ya bootstrappeado con `sdd-linear`.

Ejemplo conceptual:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py log-issue \
  --change-id demo-change \
  --title "Derived issue stub test" \
  --summary "Probando Phase 2 con runtime stub" \
  --blocking false \
  --engram-observation-id 2001 \
  --runtime-mode stub
```

Qué revisar en metadata:

- `adapterOutcomes`
- estados normalizados
- `reconciliation-required` si aplica

---

## Paso 6 — Probar el guard rail de live mode

Revisá que los wrappers y el core **no permitan** un live casual sin opt-in explícito.

Lo que querés comprobar es esto:

- `stub` es el default
- `live` no es accidental
- `live` requiere confirmación explícita del operador

---

## Paso 7 — Revisar qué falta para tu cuenta real

Para conectar esto con tu cuenta real de Linear y Engram, todavía falta:

### Linear real

- un handler real para:
  - `sync_status`
  - `log_issue`
  - `archive`
- credenciales / acceso MCP real
- scope seguro para smoke/live

### Engram real

- un handler real para guardar observaciones/eventos
- estrategia de linkage/update después del éxito en Linear

### Config operacional

- configuración explícita para live
- política de proyectos permitidos
- política de close real

---

## Cómo sabremos que ya se integra con tu cuenta real

Lo vas a poder afirmar recién cuando exista todo esto:

- live handlers reales implementados
- preflight conectado a credenciales reales
- smoke target definido
- prueba real que cree/comente/actualice algo en tu workspace
- evidencia persistida en metadata local con remote IDs reales

Hasta ese momento, la afirmación honesta es:

> “Fase 2 ya tiene la arquitectura runtime/live, pero todavía no está conectada de forma real a mi cuenta de Linear/Engram.”

---

## Próximo paso recomendado

Antes del archive de Fase 2, usá este documento como checklist de revisión final.

Si querés avanzar hacia tu cuenta real, el siguiente change debería ser algo como:

- `linear-live-handlers`

o

- `linear-engram-live-wiring`

porque ese siguiente paso ya no es de arquitectura/runtime genérico, sino de **wiring real contra tus sistemas**.
