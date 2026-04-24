# PHASE-2-CHECKLIST.md

## Objetivo

Usar este checklist para validar **Phase 2** de `sdd-linear` antes de cerrarla definitivamente.

> Este checklist valida la **arquitectura runtime/live-ready** y su comportamiento actual.
> NO valida todavía wiring real por defecto contra tu cuenta real de Linear/Engram.

---

## Regla de cierre de esta fase

Podemos considerar **Phase 2 cerrable** si se cumplen estas 3 condiciones:

1. **Arquitectura runtime** validada
2. **Tests automáticos** en verde
3. **Comportamiento live-safe** comprobado sin ambigüedad

---

## Checklist ejecutiva

- [ ] Confirmar que `runtime.mode` default es `stub`
- [ ] Confirmar que `allowedModes` incluye `stub` y `live`
- [ ] Confirmar que `live` requiere opt-in explícito
- [ ] Confirmar que existe preflight runtime
- [ ] Confirmar que existe adapter `live` y adapter `stub`
- [ ] Confirmar que wrappers OpenCode documentan `runtimeMode`
- [ ] Confirmar que wrappers OpenCode exigen confirmación explícita para `live`
- [ ] Confirmar que el helper skill sigue siendo opcional
- [ ] Confirmar que `status` usa adapter dispatch + persiste outcomes
- [ ] Confirmar que `log-issue` soporta partial success y `reconciliation-required`
- [ ] Confirmar que `archive` aplica smoke-policy y outcomes normalizados
- [ ] Ejecutar tests de Phase 2 con el comando canónico
- [ ] Confirmar que el comando canónico descubre tests de verdad
- [ ] Confirmar que `python3 -m unittest` en root NO es el comando correcto
- [ ] Confirmar que bootstrap ya incluye archivos runtime nuevos
- [ ] Confirmar que la fase sigue siendo safe-by-default
- [ ] Dejar explícito qué NO cubre esta fase

---

## Paso 1 — Validar config runtime

Archivo:

```text
.ai/workflows/sdd-linear/config.json
```

Checklist:

- [ ] `runtime.mode = stub`
- [ ] `allowedModes = ["stub", "live"]`
- [ ] `runtime.live.requireExplicitOptIn = true`
- [ ] `runtime.live.preflight.credentials = true`
- [ ] `runtime.live.preflight.connectivity = true`
- [ ] `runtime.live.preflight.targetScope = true`
- [ ] `runtime.live.smokePolicy.allowClose = false`

Resultado esperado:

- la configuración confirma que **live existe**, pero **stub sigue siendo el default seguro**

---

## Paso 2 — Validar adapters runtime

Archivos:

```text
.ai/workflows/sdd-linear/runtime/adapters/stub.py
.ai/workflows/sdd-linear/runtime/adapters/live.py
.ai/workflows/sdd-linear/runtime/ports.py
.ai/workflows/sdd-linear/runtime/preflight.py
```

Checklist:

- [ ] existe `stub.py`
- [ ] existe `live.py`
- [ ] existe `ports.py`
- [ ] existe `preflight.py`
- [ ] `live.py` usa handlers inyectables
- [ ] `live.py` falla seguro si una operación no está configurada
- [ ] `stub.py` genera outcomes deterministas

Resultado esperado:

- la fase tiene arquitectura runtime completa
- no hay side effects live accidentales por default

---

## Paso 3 — Validar wrappers OpenCode

Archivos:

- `.opencode/commands/sdd-linear/sdd-new.md`
- `.opencode/commands/sdd-linear/sdd-status.md`
- `.opencode/commands/sdd-linear/sdd-log-issue.md`
- `.opencode/commands/sdd-linear/sdd-archive.md`

Checklist:

- [ ] documentan `runtimeMode`
- [ ] documentan `stub|live`
- [ ] exigen frase explícita para `live`
- [ ] siguen siendo wrappers finos
- [ ] no duplican reglas del workflow

Frase esperada:

```text
ALLOW_SDD_LINEAR_LIVE
```

Resultado esperado:

- live mode requiere intención explícita del operador

---

## Paso 4 — Validar helper skill

Archivo:

```text
.atl/skills/sdd-linear-flow/SKILL.md
```

Checklist:

- [ ] existe
- [ ] sigue siendo opcional
- [ ] no rompe la operación si no está presente
- [ ] acompaña runtime UX pero no secuestra el core

Resultado esperado:

- helper útil, pero no obligatoria

---

## Paso 5 — Validar dispatch real en core

Archivo:

```text
.ai/workflows/sdd-linear/bin/sdd_linear_core.py
```

Checklist:

- [ ] `status` despacha vía runtime adapter
- [ ] `log-issue` despacha vía runtime adapter
- [ ] `archive` despacha vía runtime adapter
- [ ] persiste `adapterOutcomes`
- [ ] persiste bloqueos de preflight/live
- [ ] mantiene compatibilidad con comportamiento de Phase 1

Resultado esperado:

- el core conserva ownership del workflow, pero usa adapters para side effects

---

## Paso 6 — Validar partial success y reconciliación

Archivo a revisar conceptualmente:

```text
.ai/workflows/sdd-linear/contracts/derived-issue.schema.json
```

Checklist:

- [ ] existe `reconciliation-required`
- [ ] existe manejo de `Engram success / Linear fail`
- [ ] existe manejo de `Linear success / Engram follow-up fail`
- [ ] el guidance prohíbe duplicar el issue ya creado en Linear

Resultado esperado:

- la fase modela split-brain de manera explícita y recuperable

---

## Paso 7 — Ejecutar tests correctos

Comando canónico:

```bash
python3 -m unittest discover -s tests
```

Checklist:

- [ ] el comando corre tests de verdad
- [ ] todos los tests pasan
- [ ] baseline actual esperado: **31 tests**

Resultado esperado:

- Phase 2 validada por suite automatizada

---

## Paso 8 — Confirmar comando incorrecto conocido

Comando a NO usar como verificación canónica:

```bash
python3 -m unittest
```

Checklist:

- [ ] confirmar que este comando no es confiable en este repo
- [ ] dejar asentado que el comando correcto es `discover -s tests`

Resultado esperado:

- el equipo no se engaña con un comando que descubre 0 tests

---

## Paso 9 — Validar bootstrap Phase 2

Archivo:

```text
scripts/bootstrap-sdd-linear.sh
```

Checklist:

- [ ] incluye archivos runtime nuevos
- [ ] sigue siendo idempotente
- [ ] no copia secretos
- [ ] no activa live automáticamente

Resultado esperado:

- bootstrap alineado con el estado actual del workflow

---

## Paso 10 — Cerrar expectativas de negocio

Antes de cerrar la fase, confirmar explícitamente esto:

### Sí cubre Phase 2

- [ ] runtime architecture lista
- [ ] ports + adapters listos
- [ ] stub/live model listo
- [ ] preflight listo
- [ ] wrappers/runtime UX lista
- [ ] outcomes normalizados listos
- [ ] reconciliación lista

### NO cubre todavía Phase 2

- [ ] wiring real por defecto a tu cuenta de Linear
- [ ] wiring real por defecto a tu cuenta de Engram
- [ ] side effects reales garantizados en tu workspace
- [ ] smoke test real con cuenta productiva

Resultado esperado:

- cerramos esta fase con honestidad arquitectónica

---

## Criterio final de cierre

Podés cerrar **Phase 2** si marcás todo esto como cumplido:

- [ ] config runtime validada
- [ ] adapters runtime validados
- [ ] wrappers OpenCode validados
- [ ] helper skill validada
- [ ] dispatch del core validado
- [ ] reconciliación validada
- [ ] tests automáticos en verde
- [ ] comando de verify canónico confirmado
- [ ] bootstrap alineado
- [ ] límites de la fase explicitados

Si esto está todo en verde:

> **Phase 2 está cerrable**.

Y el siguiente paso natural ya no es “mejorar runtime”, sino:

> **wirear live handlers reales para tu cuenta de Linear + Engram**.
