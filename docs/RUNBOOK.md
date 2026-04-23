# RUNBOOK.md

## Objetivo

Probar manualmente la **Fase 1** de `sdd-linear` en este repo.

> Importante: Fase 1 valida principalmente **contracts/outputs + persistencia local**.
> No exige side effects reales contra Linear MCP como parte obligatoria del alcance actual.

---

## Runtime actual: ¿se usa siempre Python?

**Hoy, sí:** la implementación actual de Fase 1 usa **`python3`** como runtime del core neutral.

Eso se ve en los wrappers OpenCode, por ejemplo:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py new
```

### Qué significa esto realmente

- **Sí, para probar Fase 1 hoy necesitás `python3` disponible**.
- **No significa que la arquitectura quede casada para siempre con Python**.
- El diseño sigue siendo **core neutral + adapters**, así que más adelante el runtime podría migrarse si hiciera falta.

### Dependencias Python actuales

En esta Fase 1:

- no hay `requirements.txt`
- no hay `pyproject.toml`
- no hay instalación por `pip`
- se usa solamente **Python estándar** + `unittest`

O sea: si tenés `python3`, ya podés correr y probar lo actual.

---

## Instalación en OpenCode

La instalación en OpenCode para Fase 1 es **project-local**, no global.

### Opción A — ya estás en este repo

Si ya clonaste este repo, no tenés que “instalar un paquete”.
Solo necesitás:

1. Tener `python3`
2. Tener este repo en disco
3. Asegurarte de que OpenCode descubra:
   - `.opencode/commands/sdd-linear/`
   - `.atl/skills/sdd-linear-flow/` (opcional)

En ese caso, alcanzaría con tu paso normal de refresh/sync del agente.

### Opción B — instalarlo en otro proyecto usando bootstrap

Desde este repo fuente, corré:

```bash
bash ./scripts/bootstrap-sdd-linear.sh <ruta-del-proyecto-destino> --dry-run
```

Si el plan se ve bien:

```bash
bash ./scripts/bootstrap-sdd-linear.sh <ruta-del-proyecto-destino> --yes
```

Eso copia los paths gestionados al proyecto destino, incluyendo:

- `./.ai/workflows/sdd-linear/`
- `./.opencode/commands/sdd-linear/`
- `./.atl/skills/sdd-linear-flow/SKILL.md`

### Después del bootstrap

Tenés que hacer el refresh normal del agente para que OpenCode vea los comandos/skills del proyecto.

En términos prácticos, el checklist es:

1. bootstrap
2. sync/refresh del agente
3. verificar comandos project-local
4. recién ahí probar `/sdd-new`, `/sdd-status`, etc.

### Qué NO hace la instalación

La instalación actual **no**:

- instala Python
- instala dependencias por pip
- configura secretos de Linear
- autentica automáticamente Engram o Linear
- registra nada globalmente fuera del proyecto

Todo eso queda explícitamente fuera del bootstrap de Fase 1.

---

## Qué deberías tener en este repo

- `./.ai/workflows/sdd-linear/`
- `./.opencode/commands/sdd-linear/`
- `./scripts/bootstrap-sdd-linear.sh`
- `./tests/test_sdd_linear_batch4.py`

---

## Prerrequisitos para probar Fase 1

Necesitás:

- `python3`
- shell POSIX compatible para correr el bootstrap (`bash`)
- repo clonado localmente
- opcionalmente OpenCode / gentle-ai refrescado para descubrir comandos project-local

Chequeos rápidos:

```bash
python3 --version
bash --version
```

Si `python3` no existe, Fase 1 actual no va a correr. Es así de simple.

---

## 1. Ver estructura base

Corré:

```bash
ls .ai/workflows/sdd-linear
ls .opencode/commands/sdd-linear
ls scripts
```

Deberías ver al menos:

- `config.json`
- `state-map.json`
- `contracts/`
- `templates/`
- `changes/`
- `bin/sdd_linear_core.py`
- wrappers `sdd-new.md`, `sdd-status.md`, `sdd-log-issue.md`, `sdd-archive.md`
- `bootstrap-sdd-linear.sh`

---

## 2. Ejecutar la suite de tests

Corré:

```bash
python3 -m unittest discover -s tests -p "test*.py"
```

Resultado esperado:

- todos los tests en verde
- hoy el baseline esperado es **15 passed**

---

## 3. Probar `/sdd-new` creando un cambio

Elegí un change de prueba, por ejemplo `demo-change`.

Corré:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py new \
  --change-id demo-change \
  --title "Demo change" \
  --linear-issue-id LIN-123
```

Verificá que exista:

```bash
ls .ai/workflows/sdd-linear/changes
```

Debería aparecer un archivo tipo:

- `demo-change.json`

Después abrilo y confirmá que tenga:

- `changeId`
- `linear.issueId`
- estado inicial del workflow

---

## 4. Probar fallo de `/sdd-new` sin Linear issue

Corré:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py new \
  --change-id demo-missing-linear \
  --title "Should fail"
```

Resultado esperado:

- debe fallar
- **no** debe crear metadata para ese change

Verificá:

```bash
ls .ai/workflows/sdd-linear/changes
```

No debería existir `demo-missing-linear.json`.

---

## 5. Probar `/sdd-status`

Actualizá el estado del change creado:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py status \
  --change-id demo-change \
  --sdd-state review
```

Qué validar:

- devuelve el estado SDD local
- devuelve el estado Linear mapeado desde `state-map.json`
- persiste el nuevo estado en `demo-change.json`

Tip:

- revisá `state-map.json`
- confirmá que el mapping sea el esperado (`Backlog`, `In Progress`, `Done` en Fase 1)

---

## 6. Probar `/sdd-log-issue` con fallback manual

Acá lo importante en Fase 1 es validar:

- orden Engram-first a nivel contrato
- retry bounded
- payload/prompt manual si falla
- persistencia local del resultado

Corré algo como:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py log-issue \
  --change-id demo-change \
  --engram-observation-id 999 \
  --title "Derived issue demo" \
  --blocking true
```

Qué validar en `demo-change.json`:

- existe `derivedIssues`
- se registra `engramObservationId`
- aparecen intentos/retries
- si no hubo resolución, aparece `manualFallback`
  - `required`
  - `payload`
  - `prompt`

---

## 7. Probar `/sdd-archive` fallando por gates incompletos

Corré:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py archive \
  --change-id demo-change
```

Resultado esperado:

- debe bloquear archive
- debe listar faltantes

Qué validar en metadata:

- `archive.gate.status = blocked`
- `archive.gate.missing` contiene campos faltantes

Campos mínimos requeridos en Fase 1:

- `prUrl`
- `mergeConfirmed`
- `qaNotes`
- `businessValidation`

---

## 8. Probar `/sdd-archive` con gates completos

Corré con evidencia completa:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py archive \
  --change-id demo-change \
  --pr-url "https://github.com/example/repo/pull/123" \
  --merge-confirmed true \
  --qa-notes "QA manual OK" \
  --business-validation "Producto validado"
```

Qué validar:

- `archive.gate.status = pass`
- se renderiza comentario final
- quedan flags de elegibilidad de cierre/comentario

Importante:

> En Fase 1 esto valida el **artifact/render/eligibility contract**.
> No implica necesariamente que ya se haya ejecutado un comentario o cierre real en Linear.

---

## 9. Probar wrappers OpenCode

Abrí estos archivos:

- `.opencode/commands/sdd-linear/sdd-new.md`
- `.opencode/commands/sdd-linear/sdd-status.md`
- `.opencode/commands/sdd-linear/sdd-log-issue.md`
- `.opencode/commands/sdd-linear/sdd-archive.md`

Qué validar:

- apuntan al core neutral
- no duplican reglas de negocio
- reflejan que la helper skill es opcional

---

## 10. Probar bootstrap en modo seguro

Primero dry-run:

```bash
bash ./scripts/bootstrap-sdd-linear.sh . --dry-run
```

Qué validar:

- no escribe archivos
- muestra plan
- reporta archivos a crear/modificar/omitir

Después probá re-ejecución idempotente:

```bash
bash ./scripts/bootstrap-sdd-linear.sh . --yes
```

Y luego otra vez:

```bash
bash ./scripts/bootstrap-sdd-linear.sh . --yes
```

Resultado esperado:

- no duplica estructuras
- reporta `no changes` o equivalente

---

## 11. Qué significa “Fase 1 funcionando”

Podés dar por válida Fase 1 si comprobás esto:

- `new` exige `linearIssueId`
- `status` usa `state-map.json`
- `log-issue` registra derived issues con retries + fallback manual
- `archive` bloquea sin evidencia y pasa con evidencia completa
- la metadata local en `changes/*.json` refleja el flujo
- los tests pasan
- bootstrap es idempotente
- wrappers consumen el core neutral

---

## 12. Qué NO estás probando todavía

Todavía NO estás probando obligatoriamente en Fase 1:

- creación real de issue en Linear MCP
- comentario real en Linear
- cierre real de issue en Linear
- ejecución end-to-end del adapter OpenCode dentro del runtime real del agente

Eso pertenece a una **Fase 2 runtime/live integration**.

---

## 13. Checklist rápida

- [ ] estructura base presente
- [ ] tests verdes
- [ ] `new` exitoso con `linearIssueId`
- [ ] `new` falla sin `linearIssueId`
- [ ] `status` persiste mapping correcto
- [ ] `log-issue` deja retry/fallback en metadata
- [ ] `archive` bloquea sin evidencia
- [ ] `archive` pasa con evidencia completa
- [ ] wrappers OpenCode apuntan al core
- [ ] bootstrap dry-run OK
- [ ] bootstrap re-run idempotente
