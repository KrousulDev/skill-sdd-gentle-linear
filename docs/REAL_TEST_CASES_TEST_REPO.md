# REAL_TEST_CASES_TEST_REPO.md

## Objetivo

Definir un **test case real** para validar `sdd-linear` Fase 1 usando proyectos reales ubicados en:

- `/Users/kikemedina/Develop/git/github/test/codex5.4`
- `/Users/kikemedina/Develop/git/github/test/spark`

La idea NO es probar Linear MCP real todavía.
La idea es probar que el workflow de Fase 1:

- se puede instalar en un proyecto real
- genera metadata local correctamente
- obliga `linearIssueId`
- registra estados
- registra derived issues
- evalúa archive gates
- funciona sobre proyectos ajenos al repo fuente

---

## Resumen de los proyectos bajo prueba

### 1. `codex5.4`

- App: **Tetris Orbital**
- Stack: HTML + CSS + JavaScript vanilla
- Entrada principal: `index.html`
- Script principal: `script.js`
- README ya indica server local con:

```bash
python3 -m http.server 8080
```

### 2. `spark`

- App: **Tetris en JavaScript**
- Stack: HTML + CSS + JavaScript vanilla
- Entrada principal: `index.html`
- Script principal: `app.js`

---

## Alcance del test real

Este test valida Fase 1 en dos dimensiones:

1. **Instalación/portabilidad**
   - bootstrap sobre un proyecto destino real
   - wrappers/skills/core presentes en el proyecto destino

2. **Flujo funcional local de Fase 1**
   - `new`
   - `status`
   - `log-issue`
   - `archive`

---

## Precondiciones

Necesitás:

- `python3`
- `bash`
- repo fuente actual disponible:
  - `/Users/kikemedina/Develop/git/github/skill-sdd-gentle-linear`
- proyecto destino real:
  - `/Users/kikemedina/Develop/git/github/test/codex5.4`
  - `/Users/kikemedina/Develop/git/github/test/spark`

Chequeos:

```bash
python3 --version
bash --version
```

---

## Estrategia recomendada

Vamos a probar primero en `codex5.4` y después repetir casi igual en `spark`.

¿Por qué así?

- `codex5.4` ya tiene README y controles más completos
- `spark` nos sirve como segundo smoke test de portabilidad

---

# Caso A — Probar instalación y flujo en `codex5.4`

## A.1 Instalar `sdd-linear` en el proyecto destino

Desde este repo fuente corré:

```bash
bash ./scripts/bootstrap-sdd-linear.sh /Users/kikemedina/Develop/git/github/test/codex5.4 --dry-run
```

### Resultado esperado

- no escribe nada
- muestra plan
- lista archivos gestionados

Si el plan se ve bien:

```bash
bash ./scripts/bootstrap-sdd-linear.sh /Users/kikemedina/Develop/git/github/test/codex5.4 --yes
```

### Resultado esperado

El proyecto destino debería ganar al menos:

- `.ai/workflows/sdd-linear/`
- `.opencode/commands/sdd-linear/`
- `.atl/skills/sdd-linear-flow/SKILL.md`

---

## A.2 Verificar estructura instalada en `codex5.4`

Corré:

```bash
ls /Users/kikemedina/Develop/git/github/test/codex5.4/.ai/workflows/sdd-linear
ls /Users/kikemedina/Develop/git/github/test/codex5.4/.opencode/commands/sdd-linear
ls /Users/kikemedina/Develop/git/github/test/codex5.4/.atl/skills/sdd-linear-flow
```

### Resultado esperado

- core neutral presente
- wrappers presentes
- helper skill presente

---

## A.3 Levantar la app destino para contexto humano

Desde:

```bash
/Users/kikemedina/Develop/git/github/test
```

corré:

```bash
python3 -m http.server 8080
```

Abrí:

```text
http://localhost:8080/codex5.4/
```

### Validación humana esperada

- carga la UI de **Tetris Orbital**
- se ve score, líneas, nivel, next, hold y controles

> Esto no prueba `sdd-linear` todavía. Solo prueba que el proyecto destino existe y tiene sentido funcional.

---

## A.4 Crear un cambio SDD real para `codex5.4`

Desde el proyecto destino:

```bash
cd /Users/kikemedina/Develop/git/github/test/codex5.4
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py new \
  --change-id codex-ui-check \
  --title "Validar instalación y flujo Fase 1 en Tetris Orbital" \
  --linear-issue-id LIN-CODEX-001
```

### Resultado esperado

- crea metadata en:

```text
.ai/workflows/sdd-linear/changes/codex-ui-check.json
```

- el JSON debe tener:
  - `changeId`
  - `linear.issueId = LIN-CODEX-001`
  - estado inicial

---

## A.5 Probar que `linearIssueId` es obligatorio

Corré:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py new \
  --change-id codex-should-fail \
  --title "Esto debe fallar"
```

### Resultado esperado

- falla
- NO crea:

```text
.ai/workflows/sdd-linear/changes/codex-should-fail.json
```

---

## A.6 Actualizar estado

Corré:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py status \
  --change-id codex-ui-check \
  --sdd-state review
```

### Resultado esperado

- respuesta con estado SDD local
- estado Linear mapeado
- persistencia en `codex-ui-check.json`

Validación recomendada:

- abrir `state-map.json`
- abrir `changes/codex-ui-check.json`

---

## A.7 Registrar issue derivado

Supongamos que encontraste este problema manualmente:

> “El botón de pausa existe pero quiero registrar una observación de UX sobre claridad del overlay”.

Corré:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py log-issue \
  --change-id codex-ui-check \
  --engram-observation-id 1001 \
  --title "Revisar claridad del overlay de pausa" \
  --blocking false
```

### Resultado esperado

En el JSON del change debería aparecer:

- `derivedIssues`
- `engramObservationId`
- retries / attempts
- `manualFallback` si no se resolvió integración externa

---

## A.8 Probar archive bloqueado

Corré:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py archive \
  --change-id codex-ui-check
```

### Resultado esperado

- bloquea
- lista faltantes

Campos esperados como missing:

- `prUrl`
- `mergeConfirmed`
- `qaNotes`
- `businessValidation`

---

## A.9 Probar archive exitoso

Corré:

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py archive \
  --change-id codex-ui-check \
  --pr-url "https://github.com/example/codex5.4/pull/1" \
  --merge-confirmed true \
  --qa-notes "Se validó carga de UI y flujo manual base" \
  --business-validation "Aceptado como prueba manual Fase 1"
```

### Resultado esperado

- `archive.gate.status = pass`
- comentario renderizado
- elegibilidad de cierre/comentario

> Recordatorio: en Fase 1 esto sigue siendo contract/output, no side effect real obligatorio en Linear.

---

# Caso B — Repetir portabilidad en `spark`

## B.1 Instalar en `spark`

Desde el repo fuente:

```bash
bash ./scripts/bootstrap-sdd-linear.sh /Users/kikemedina/Develop/git/github/test/spark --dry-run
bash ./scripts/bootstrap-sdd-linear.sh /Users/kikemedina/Develop/git/github/test/spark --yes
```

### Resultado esperado

- misma estructura instalada que en `codex5.4`
- prueba de portabilidad entre proyectos reales distintos

---

## B.2 Levantar la app destino

Desde:

```bash
/Users/kikemedina/Develop/git/github/test
```

corré:

```bash
python3 -m http.server 8080
```

Abrí:

```text
http://localhost:8080/spark/
```

### Validación humana esperada

- carga la UI de Tetris
- se ve HUD con score, líneas, nivel
- aparecen botones Start / Reiniciar y Pausar

---

## B.3 Crear cambio real en `spark`

Desde el proyecto destino:

```bash
cd /Users/kikemedina/Develop/git/github/test/spark
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py new \
  --change-id spark-smoke-test \
  --title "Validar instalación y flujo Fase 1 en Spark Tetris" \
  --linear-issue-id LIN-SPARK-001
```

### Resultado esperado

- metadata creada en:

```text
.ai/workflows/sdd-linear/changes/spark-smoke-test.json
```

---

## B.4 Actualizar estado en `spark`

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py status \
  --change-id spark-smoke-test \
  --sdd-state apply
```

### Resultado esperado

- mapping correcto a estado Linear
- persistencia local OK

---

## B.5 Registrar derived issue en `spark`

Ejemplo de observación manual:

> “El texto de status podría ser más claro al pausar/reanudar”.

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py log-issue \
  --change-id spark-smoke-test \
  --engram-observation-id 1002 \
  --title "Clarificar texto de status al pausar" \
  --blocking false
```

### Resultado esperado

- metadata de derived issue persistida
- retry/fallback presente si corresponde

---

## B.6 Archive exitoso en `spark`

```bash
python3 ./.ai/workflows/sdd-linear/bin/sdd_linear_core.py archive \
  --change-id spark-smoke-test \
  --pr-url "https://github.com/example/spark/pull/1" \
  --merge-confirmed true \
  --qa-notes "HUD y controles visibles; smoke test manual correcto" \
  --business-validation "Aprobado para prueba de portabilidad"
```

### Resultado esperado

- gates en pass
- comentario renderizado
- metadata final consistente

---

## Criterios de éxito globales

El test real se considera exitoso si:

- [ ] `codex5.4` recibe instalación correcta vía bootstrap
- [ ] `spark` recibe instalación correcta vía bootstrap
- [ ] ambos proyectos pueden crear metadata local con `new`
- [ ] ambos bloquean creación sin `linearIssueId`
- [ ] ambos actualizan estado con `status`
- [ ] ambos registran derived issue con retry/fallback local
- [ ] ambos bloquean archive incompleto
- [ ] ambos permiten archive con evidencia mínima completa
- [ ] no se rompe el proyecto frontend destino por instalar `sdd-linear`

---

## Qué demuestra este test case

Si todo esto pasa, demuestra que Fase 1 ya sirve para:

- instalarse sobre proyectos reales externos
- mantener el core neutral reusable
- operar con Python estándar sin dependencias extra
- persistir trazabilidad local mínima por cambio
- validar que OpenCode puede consumir el workflow como capa project-local

---

## Qué NO demuestra todavía

Este test case todavía NO demuestra:

- creación real de issues en Linear MCP
- comentario real en Linear
- cierre real de issue en Linear
- ejecución real end-to-end del runtime OpenCode dentro del agente

Eso sigue siendo trabajo de **Fase 2 runtime/live integration**.
