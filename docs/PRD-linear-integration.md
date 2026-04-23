# PRD-linear-integration.md

> Product Requirements Document para integrar Linear al workflow SDD + Engram del proyecto.
> Enfocado en trazabilidad completa de issues, features, sesiones, evidencias y portabilidad de configuración entre máquinas.

---

## 0. Metadata

**Product Name:** SDD + Engram + Linear Integration  
**Version:** 1.2  
**Author:** OpenAI Assistant  
**Date:** 2026-04-22  
**Status:** Draft - reviewed  
**Stakeholders:** Product, Engineering, QA, AI Workflow Owners  
**Related Docs:** `docs/PRD/PRD-Template.md`, `platform/.atl/skill-registry.md`, `https://github.com/Gentleman-Programming/gentle-ai/blob/main/README.md`, `https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/components.md`, `https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/opencode-profiles.md`

**Resumen:**  
Este PRD define una integración entre el workflow SDD del proyecto, la memoria persistente en Engram y la gestión operativa en Linear. El objetivo es que cada cambio iniciado con `/sdd-new` deba vincularse a un issue o feature en Linear, que los estados del trabajo se sincronicen durante la ejecución, que los hallazgos emergentes puedan convertirse en issues derivados, y que `/sdd-archive` solo cierre el trabajo cuando existan evidencias completas de implementación, QA, merge y validación de negocio.

Además, la solución debe ser portable y configurable. Si una máquina pierde su setup local, otra máquina debe poder recuperar el mismo comportamiento reutilizando una configuración declarativa, sin depender de estado oculto ni de pasos manuales frágiles. El diseño debe ser multiagente, con núcleo neutral al agente y primer adaptador operativo orientado a OpenCode dentro del ecosistema gentle-ai.

---

## 1. Problem Statement

**Objetivo:**  
Definir el problema de trazabilidad y cierre operativo entre SDD, Engram y Linear.

### Estado actual
- El proyecto ya utiliza SDD como workflow de cambio y Engram como memoria persistente.
- El repo ya contiene carpetas específicas por agente (`.atl/`, `.claude/`, `.cursor/`, `.opencode/`), por lo que atar el dominio del workflow a una sola de ellas rompería portabilidad.
- No existe una integración explícita con Linear en el repo.
- Linear será obligatorio como fuente operativa dentro del alcance de este skill/workflow (`SDD + gentle-ai + Linear`).
- La trazabilidad entre sesión, issue, feature, QA, merge y validación de negocio depende de disciplina manual.

### Problemas específicos
- Un cambio puede quedar implementado técnicamente pero no validado completamente.
- No existe un punto formal donde el estado del trabajo en Linear refleje el avance real del ciclo SDD.
- Los issues descubiertos durante la ejecución pueden perder contexto o no quedar asociados al origen.
- El cierre puede ocurrir antes de QA, merge o validación de negocio si no hay gates explícitos.
- La configuración para este flujo podría quedar implícita en una máquina y no ser reproducible en otra.
- El proyecto necesita convivir con múltiples agentes/overlays y OpenCode será el primer target operativo, pero no el único entorno posible.

### Impacto
- Riesgo de cerrar trabajo incompleto.
- Pérdida de contexto entre sesiones o entre personas/agentes.
- Baja trazabilidad de evidencias y follow-ups.
- Setup frágil y difícil de replicar.

---

## 2. Vision

**Objetivo:**  
Describir el estado ideal después de implementar la integración.

### Estado deseado
- Todo `/sdd-new` debe asociarse a un issue de Linear y opcionalmente a una feature padre.
- Linear refleja el estado vivo del cambio durante todo el ciclo SDD.
- Engram conserva el contexto fino e histórico de decisiones, descubrimientos y cierres.
- `/sdd-archive` solo se ejecuta cuando el cambio está realmente completo.
- Los issues descubiertos en ejecución pueden crearse en Linear y relacionarse automáticamente con el issue/feature origen.
- La configuración del workflow vive en archivos declarativos y versionados para ser reutilizable en cualquier máquina.
- El core del workflow vive en una carpeta neutral del repo y los agentes consumen adaptadores derivados de esa fuente de verdad.
- La integración con Linear se realiza preferentemente por MCP para agentes, no por una CLI third-party como backbone.

### Before vs After
**Before:** cambios dispersos, cierre manual, evidencias no normalizadas, setup no portable.  
**After:** ciclo trazable, estados consistentes, cierre con evidencias, configuración reproducible.

---

## 3. Target Users

**Objetivo:**  
Definir quién usa este sistema.

### Primary Users
- Engineering / AI operators: necesitan iniciar, ejecutar y cerrar cambios con trazabilidad completa.
- Product / PM: necesitan ver en Linear el estado real del trabajo y su evidencia.

### Secondary Users
- QA: necesitan checkpoints claros y evidencia de validación.
- Stakeholders de negocio: necesitan saber cuándo un issue o feature está realmente terminado.

---

## 4. User Experience (UX)

**Objetivo:**  
Definir el flujo operativo esperado.

### Entry points
- `/sdd-new`
- `/sdd-status`
- `/sdd-log-issue` o acción equivalente para issue derivado
- `/sdd-archive`
- futuro `/sdd-feature-close`
- setup/bootstrap del workflow desde CLI/TUI existente del ecosistema

### Flujo principal
1. El usuario inicia un cambio con `/sdd-new`.
2. El comando solicita o acepta `linearIssueId` y opcionalmente `linearFeatureId`.
3. El cambio queda inicializado con metadata local + referencia a Linear + política de cierre.
4. Durante la ejecución se actualiza el estado del issue en Linear.
5. Si aparece trabajo emergente, se registra obligatoriamente en Engram y se intenta crear un issue derivado en Linear ligado al origen.
6. El issue solo pasa a `ready_to_archive` cuando se cumplen todos los gates.
7. `/sdd-archive` publica comentario final, adjunta/resume evidencias y cierra el issue.
8. Si corresponde, la feature se actualiza o eventualmente se cierra cuando todos sus issues hijos estén completos.

### Modelo de feature en Linear
- **Recomendación:** representar una feature como **Project** en Linear.
- Razón: da un contenedor natural para múltiples issues/changes, permite seguimiento visible del avance y encaja mejor con el modelo “feature padre + issues hijos” que el proyecto necesita para homologar SDD + Engram + Linear.
- El issue individual sigue siendo la unidad operativa de ejecución y cierre.

### Estados del sistema
- Draft
- Active
- In Review
- QA Pending
- Business Validation Pending
- Ready to Archive
- Archived

### Estrategia inicial de estados en Linear
- En Fase 1 no se asume que el workspace ya tenga todos los estados ideales creados.
- Parte del rollout será definir y crear los estados mínimos necesarios en Linear.
- Mientras tanto, el workflow debe soportar un enfoque de **muchos estados SDD -> pocos estados reales de Linear**.
- El mapping exacto debe vivir en configuración declarativa y no hardcodeado en la lógica.

---

## 5. System / Feature Overview

**Objetivo:**  
Describir el sistema a alto nivel.

### Componentes principales
- **Neutral Workflow Core**: fuente de verdad portable del flujo SDD + Linear.
- **SDD Commands Layer**: inicia, actualiza y cierra cambios.
- **Engram Memory Layer**: persiste decisiones, descubrimientos, preferencias y cierres.
- **Linear MCP Layer**: crea, actualiza, comenta y cierra issues/features mediante agentes.
- **Agent Adapter Layer**: adapta el core neutral al agente activo, empezando por OpenCode.
- **Config Layer**: define credenciales, mapping de estados, políticas y templates.
- **Evidence Layer**: recopila links y artefactos de cierre.
- **Optional Skill Layer**: skill liviana que interpreta config y ayuda a ejecutar el flujo.

### Responsabilidades
- SDD: orquestación del workflow.
- Engram: memoria persistente y contexto histórico.
- Linear MCP: visibilidad operacional y gestión de trabajo desde agentes.
- Config: portabilidad y reproducibilidad del comportamiento.
- Agent Adapters: compatibilidad por plataforma sin mover el dominio a carpetas vendor-specific.

---

## 6. Core Functionality

**Objetivo:**  
Describir capacidades clave.

### 6.1 Inicio de cambio con asociación a Linear
- `/sdd-new` debe requerir vincular un issue de Linear.
- Debe soportar asociación opcional a una feature padre.
- Debe persistir metadata local del cambio para futuras sesiones.

### 6.2 Soporte para issue y feature
- El sistema debe distinguir entre:
  - `issue` como unidad operativa.
  - `feature-change` como cambio ligado a una feature.
- Una feature puede contener múltiples issues/changes.
- La representación recomendada de una feature en Linear es `Project`.

### 6.3 Sincronización de estados
- Los cambios de estado del workflow SDD deben mapearse a estados configurables de Linear.
- Debe existir separación entre estado de issue y estado de feature.

### 6.4 Registro de issues derivados
- Si durante implementación, review, QA o validación aparece un nuevo problema:
  - se debe registrar obligatoriamente en Engram.
  - se debe poder crear un issue derivado en Linear.
  - se debe relacionar con el issue origen.
  - se debe relacionar con la feature padre si existe.
  - se debe marcar como `blocking` o `non-blocking`.
  - si la creación en Linear falla, el sistema debe reintentar hasta 3 veces.
  - si luego de 3 reintentos sigue fallando, el sistema debe dejar evidencia clara del fallo y generar un prompt/manual payload completo para creación manual.

### 6.5 Gates de cierre
- `/sdd-archive` debe validar que existan:
  - implementación completa
  - verificación/tests
  - PR URL
  - PR mergeado
  - notas de QA
  - validación de negocio
  - evidencias asociadas

### 6.6 Comentario final y cierre en Linear
- Al archivar, el sistema debe publicar un comentario estructurado en Linear.
- Si la política lo permite y los gates están completos, debe cerrar el issue.

### 6.7 Portabilidad de configuración
- Todo comportamiento crítico debe vivir en configuración declarativa reutilizable.
- Una nueva máquina debe poder operar con el mismo flujo restaurando configuración + credenciales.

### 6.8 Compatibilidad multiagente
- El core del workflow debe ser agnóstico al agente.
- OpenCode será el primer adaptador operativo.
- La solución debe ser revisable/extensible para otros agentes soportados por gentle-ai sin mover el dominio fuera del core neutral.

### 6.9 Skill de soporte no obligatoria
- Debe existir una skill `sdd-linear-flow` orientada explícitamente al workflow `SDD + gentle-ai + Linear`.
- La skill no debe ser obligatoria para operar el core neutral del workflow.
- La skill debe leer configuración del core neutral y coordinar la interacción con el ecosistema gentle-ai.
- Su responsabilidad es aplicar reglas, coordinar skills SDD existentes y ayudar en la interacción con Linear MCP.

### 6.10 Bootstrap portable para nuevos proyectos
- Debe existir un bootstrap shell script para inicializar el workflow en un proyecto destino.
- El script debe aceptar como mínimo la ruta del proyecto destino y opcionalmente el repo/plantilla fuente.
- El script debe copiar o sincronizar el core neutral del workflow y los adaptadores mínimos requeridos.
- El script no debe convertirse en la fuente de verdad del sistema; solo instala/regenera desde la configuración declarativa.
- El script debe preparar el proyecto para continuar con `gentle-ai sync` y `skill-registry` cuando aplique.

---

## 7. Technical Architecture

**Objetivo:**  
Explicar la implementación a alto nivel.

### Componentes técnicos
- Config loader
- Agent adapter resolver
- Metadata store del cambio SDD
- Cliente/bridge de Linear MCP
- Motor de validación de gates
- Renderer de comentarios/evidencias
- Bootstrap/setup layer
- Portable bootstrap shell script

### Interfaces
- CLI / slash commands:
  - `/sdd-new`
  - `/sdd-status`
  - `/sdd-log-issue`
  - `/sdd-archive`
  - futuro `/sdd-feature-close`

### Flujo interno
1. Leer configuración declarativa.
2. Resolver adaptador por agente activo (OpenCode primero).
3. Cargar metadata del cambio si existe desde `changes/`.
4. Resolver mapping entre estado SDD y estado de Linear.
5. Ejecutar operación sobre Linear MCP.
6. Persistir resultado en metadata local + Engram.

### Principios técnicos
- Config-first, no machine-first.
- Core-neutral, adapters-specific.
- Idempotencia en actualizaciones cuando sea posible.
- Fallar con mensajes claros si faltan credenciales o gates.
- No depender de rutas o secretos hardcodeados por máquina.

### Strategy de compatibilidad
- **Core neutral:** `./.ai/workflows/sdd-linear/`
- **Primer adaptador:** OpenCode / gentle-ai ecosystem
- **Carpetas específicas de agente:** solo para adapters, overlays, skill discovery o metadata derivada
- **No permitido:** que `.atl/` o `.opencode/` sean la única fuente de verdad del flujo

### Estrategia de bootstrap
- **Script recomendado:** `./scripts/bootstrap-sdd-linear.sh`
- **Rol:** clonar/descargar plantilla, copiar archivos base, inicializar adaptadores y dejar instrucciones finales
- **No rol:** orquestar el workflow diario ni reemplazar `gentle-ai`

---

## 8. Data & Storage

**Objetivo:**  
Definir manejo de datos.

### Metadata mínima por cambio
- `changeId`
- `title`
- `type`
- `linearIssueId`
- `linearIssueUrl`
- `linearFeatureId` (opcional)
- `originIssueId` (si es derivado)
- `archivePolicy`
- `qaRequired`
- `businessValidationRequired`
- `state`
- `blockingDerivedIssues[]`
- `nonBlockingDerivedIssues[]`
- `evidence[]`

### Ubicación de metadata runtime
- La metadata local del cambio debe vivir en `./.ai/workflows/sdd-linear/changes/`.
- Cada cambio debe persistirse como artefacto independiente para facilitar portabilidad, inspección y reuso entre sesiones.

### Configuración declarativa
Se debe almacenar en archivos versionables, por ejemplo:
- `./.ai/workflows/sdd-linear/config.json`
- `./.ai/workflows/sdd-linear/state-map.json`
- `./.ai/workflows/sdd-linear/rules.json`
- `./.ai/workflows/sdd-linear/backfill.json`
- `./.ai/workflows/sdd-linear/templates/`

### Adaptadores por agente
- `./.atl/` puede contener el adaptador para OpenCode/gentle-ai y referencias a `skill-registry`.
- `./.opencode/` puede contener skill discovery o assets propios de OpenCode si hacen falta.
- Otros agentes pueden agregar adaptadores equivalentes sin duplicar el core.

### Ubicación del bootstrap
- El bootstrap portable recomendado debe vivir en `./scripts/bootstrap-sdd-linear.sh`.
- La razón es separar tooling transversal del workflow del runtime específico de `platform/`.
- `platform/scripts/` puede seguir conteniendo scripts operativos del producto, pero no debe absorber el dominio del workflow portable.

### Skill de soporte no obligatoria
- La skill `sdd-linear-flow` podrá vivir en la capa específica del agente (por ejemplo, project-local skill para OpenCode), pero deberá leer SIEMPRE el core neutral.
- El sistema debe seguir siendo operable sin esa skill, siempre que existan los comandos/config correctos.
- La ausencia de la skill no invalida el workflow; solo elimina la capa de asistencia operativa del agente.

### Credenciales
- Variables de entorno o secret manager local.
- Nunca commitear tokens.
- La configuración debe referenciar secretos, no contenerlos.

---

## 9. Integrations

**Objetivo:**  
Definir integraciones externas.

### Linear MCP
- Crear issue derivado
- Actualizar estado de issue
- Agregar comentario
- Cerrar issue
- Leer metadata mínima necesaria para validar asociaciones

### Gentle-AI / OpenCode
- Reutilizar `skill-registry` para hacer visible la skill/config del proyecto.
- Alinear el adaptador OpenCode con el modelo de SDD profiles y estrategias de sync de gentle-ai.
- Permitir que el core neutral se refleje en overlays/config del agente sin convertirse en la única fuente de verdad.

### Engram
- Guardar decisiones, descubrimientos, preferencias y cierres.
- Registrar resumen final de sesión y del cambio.
- Registrar obligatoriamente los hallazgos derivados aunque Linear no esté disponible.

---

## 10. Requirements

### 10.1 Functional Requirements

| ID | Requirement | Priority |
|----|------------|----------|
| FR-01 | `/sdd-new` debe requerir asociación a `linearIssueId` | High |
| FR-02 | `/sdd-new` debe aceptar asociación opcional a `linearFeatureId` | High |
| FR-03 | El sistema debe persistir metadata del cambio para reusar en sesiones futuras | High |
| FR-04 | El workflow debe sincronizar estados SDD con estados configurables de Linear | High |
| FR-05 | Debe existir soporte para issues derivados durante ejecución | High |
| FR-06 | Los issues derivados deben poder marcarse como blocking o non-blocking | High |
| FR-07 | `/sdd-archive` debe bloquearse si faltan gates obligatorios | High |
| FR-08 | `/sdd-archive` debe publicar comentario final estructurado en Linear | High |
| FR-09 | `/sdd-archive` debe poder cerrar el issue cuando la política y los gates lo permitan | High |
| FR-10 | El sistema debe soportar features como contenedores de múltiples issues/changes | High |
| FR-11 | Debe existir configuración declarativa reusable entre máquinas | High |
| FR-12 | Debe ser posible reconstruir el flujo en otra máquina con la misma configuración y nuevas credenciales | High |
| FR-13 | Debe existir template configurable para comentarios de avance y cierre en Linear | Medium |
| FR-14 | Debe existir validación explícita de PR mergeado, QA y business validation antes de archive | High |
| FR-15 | El core del workflow debe vivir en una carpeta neutral al agente dentro del repo | High |
| FR-16 | El primer adaptador operativo debe ser OpenCode, sin impedir adaptadores futuros para otros agentes | High |
| FR-17 | La integración con Linear para agentes debe usar MCP como mecanismo preferente | High |
| FR-18 | Debe existir una estrategia de bootstrap/setup que pueda reutilizar TUI/CLI existentes antes de crear una nueva TUI propia | Medium |
| FR-19 | Debe existir una skill `sdd-linear-flow` para gentle-ai/OpenCode, pero no debe ser obligatoria para operar el core neutral | Medium |
| FR-20 | Las features deben mapearse a `Project` en Linear como recomendación por defecto | High |
| FR-21 | Linear debe ser obligatorio para el alcance de este workflow `SDD + gentle-ai + Linear` | High |
| FR-22 | La metadata runtime del cambio debe persistirse en `./.ai/workflows/sdd-linear/changes/` | High |
| FR-23 | Los hallazgos derivados deben registrarse obligatoriamente en Engram antes o independientemente de Linear | High |
| FR-24 | La creación de issues derivados en Linear debe reintentarse hasta 3 veces antes de activar fallback manual | High |
| FR-25 | Si la creación del issue derivado en Linear falla tras 3 reintentos, el sistema debe mostrar el fallo y generar un prompt/manual payload completo para creación manual | High |
| FR-26 | En Fase 1 el workflow debe soportar mapping de múltiples estados SDD hacia pocos estados reales de Linear | High |
| FR-27 | Las evidencias mínimas de archive en Fase 1 deben incluir PR URL, merge confirmado, notas de QA y validación de negocio | High |

---

### 10.2 Non-Functional Requirements

- **Portabilidad:** la solución debe reconstituirse en otra máquina reutilizando configuración versionada.
- **Compatibilidad:** el dominio del flujo no puede quedar acoplado a un único agente o carpeta vendor-specific.
- **Seguridad:** los secretos deben ir fuera del repo.
- **Confiabilidad:** el sistema debe evitar cierres prematuros.
- **Trazabilidad:** cada transición relevante debe quedar registrada en Linear y/o Engram.
- **Mantenibilidad:** mappings de estado y templates no deben estar hardcodeados en lógica dispersa.

---

## 11. Screens / Interfaces

### `/sdd-new`
- Propósito: iniciar cambio y asociarlo a Linear.
- Acciones: capturar metadata, persistir contexto, sincronizar inicio.

### `/sdd-status`
- Propósito: actualizar estado del cambio.
- Acciones: cambiar estado local y sincronizar con Linear.

### `/sdd-log-issue`
- Propósito: registrar hallazgo emergente como issue derivado.
- Acciones: registrar el hallazgo en Engram, intentar crear issue en Linear, asociarlo al origen, definir si bloquea y activar fallback manual si falla tras 3 reintentos.

### `/sdd-archive`
- Propósito: cerrar formalmente el cambio.
- Acciones: validar gates, publicar evidencia, cerrar issue.

### futuro `/sdd-feature-close`
- Propósito: cerrar una feature cuando todos sus issues y validaciones globales estén completos.

### Bootstrap / Setup
- Propósito: instalar o regenerar el adaptador del agente a partir del core neutral.
- Recomendación: reutilizar TUI/CLI existente del ecosistema (`gentle-ai`) y agregar un bootstrap script liviano antes de construir una TUI shell propia.
- Contrato mínimo esperado del script:
  - `bootstrap-sdd-linear.sh <target-path>`
  - flags opcionales para `--source-repo`, `--agent`, `--force`, `--dry-run`
  - validación de ruta destino
  - copia/sync de `./.ai/workflows/sdd-linear/`
  - instalación del adaptador inicial para OpenCode cuando corresponda
  - salida final con checklist de `gentle-ai sync`, `skill-registry` y configuración de secretos

### Contrato formal del bootstrap script

**Nombre recomendado:** `scripts/bootstrap-sdd-linear.sh`

**Objetivo contractual:**
Inicializar o regenerar en un proyecto destino la estructura mínima del workflow `sdd-linear` a partir de una plantilla/repo fuente, sin convertir el script en la fuente de verdad del sistema.

#### Firma base

```bash
bootstrap-sdd-linear.sh <target-path>
```

#### Firma extendida

```bash
bootstrap-sdd-linear.sh <target-path> \
  [--source-repo <git-url|local-path>] \
  [--agent <opencode|claude-code|cursor|gemini-cli|auto>] \
  [--ref <branch|tag|commit>] \
  [--force] \
  [--dry-run] \
  [--yes]
```

#### Inputs obligatorios
- `target-path`: ruta absoluta o relativa del proyecto destino.

#### Inputs opcionales
- `--source-repo`: repo o path local desde donde obtener la plantilla/config base.
- `--agent`: adaptador inicial a instalar; por defecto `opencode` o `auto` según estrategia final.
- `--ref`: branch/tag/commit a usar cuando `source-repo` sea git.
- `--force`: permite sobrescribir archivos gestionados por el bootstrap.
- `--dry-run`: muestra el plan sin escribir archivos.
- `--yes`: omite prompts de confirmación cuando aplique.

#### Precondiciones
- El `target-path` debe existir o poder crearse de manera segura.
- Si `source-repo` es remoto, git debe estar disponible.
- Si el proyecto ya contiene configuración previa, el script debe detectarla antes de modificarla.

#### Outputs esperados
- Core neutral instalado o actualizado en:
  - `./.ai/workflows/sdd-linear/`
- Adaptador inicial instalado si aplica, por ejemplo:
  - metadata o references en `.atl/`
  - assets específicos en `.opencode/` si fueran necesarios
- Resumen final en consola con:
  - archivos creados
  - archivos actualizados
  - archivos omitidos
  - pasos manuales pendientes

#### Postcondiciones
- El proyecto queda listo para correr:
  - `skill-registry`
  - `gentle-ai sync` (si aplica al agente)
- El proyecto NO queda autenticado automáticamente contra Linear; los secretos siguen siendo paso explícito del usuario.

#### Comportamiento mínimo
1. Resolver origen de plantilla.
2. Validar proyecto destino.
3. Detectar si ya existe `./.ai/workflows/sdd-linear/`.
4. Mostrar plan de acción.
5. Copiar o sincronizar archivos del core neutral.
6. Instalar adaptador inicial para el agente seleccionado.
7. No copiar secretos ni credenciales.
8. Imprimir checklist final de activación.

#### Reglas de seguridad
- Nunca sobrescribir silenciosamente archivos existentes sin `--force` o confirmación explícita.
- Nunca copiar tokens, secretos ni credenciales de Linear.
- Nunca asumir que `.atl/` o `.opencode/` son la fuente de verdad.

#### Reglas de idempotencia
- Reejecutar el script no debe duplicar estructuras.
- Si los archivos ya coinciden, el script debe reportar `no changes` o equivalente.
- Si hay drift local, el script debe reportarlo claramente antes de sobrescribir.

#### Modo dry-run
- Debe listar:
  - origen de plantilla
  - destino
  - archivos a crear
  - archivos a modificar
  - archivos en conflicto
- No debe escribir nada en disco.

#### Checklist final esperado
- Configurar secretos/credenciales de Linear MCP.
- Revisar/ajustar `./.ai/workflows/sdd-linear/*.json`.
- Ejecutar `skill-registry`.
- Ejecutar `gentle-ai sync` si el agente activo usa assets gestionados.
- Validar que el adaptador inicial quedó correctamente enlazado al core neutral.

---

## 12. Edge Cases & Error Handling

| Scenario | Behavior |
|----------|----------|
| No hay `linearIssueId` en `/sdd-new` | Rechazar con error claro porque Linear es obligatorio en este workflow |
| Falta token de Linear | Rechazar sincronización y mostrar instrucciones de setup |
| Issue derivado bloqueante abierto | Impedir `ready_to_archive` y `archive` |
| QA incompleto | Impedir `archive` |
| PR no mergeado | Impedir `archive` |
| Validación de negocio ausente | Impedir `archive` |
| Falla creación de issue derivado en Linear | Registrar en Engram, reintentar hasta 3 veces y luego generar payload/prompt manual con contexto completo |
| Config perdida en una máquina | Permitir restauración desde archivos versionados + reinyectar secretos |
| Mapping de estado inválido | Fallar con validación de config antes de operar |
| El proyecto se abre en otro agente distinto a OpenCode | El adaptador específico puede faltar, pero el core neutral debe seguir siendo válido y reusable |
| La skill `sdd-linear-flow` no está instalada | El flujo debe seguir siendo ejecutable mediante config + comandos existentes; solo se pierde la capa de asistencia operativa del agente |
| El bootstrap se ejecuta sobre un proyecto ya inicializado | Debe soportar `dry-run`, validación previa y confirmación o modo `--force` para evitar sobreescrituras accidentales |

---

## 13. Success Metrics

- % de cambios SDD vinculados a issue de Linear.
- % de cambios archivados con evidencias completas.
- % de issues derivados registrados vs hallazgos informales.
- Tiempo de recuperación del workflow en una nueva máquina.
- Reducción de cierres prematuros o sin QA.

---

## 14. Implementation Notes

- Empezar por soporte de issue-level antes de feature-level close completo.
- Diseñar mapping de estados como archivo externo.
- En Fase 1 mapear múltiples estados SDD a pocos estados reales de Linear mientras se definen y crean estados más completos en el workspace.
- Diseñar templates Markdown para comentarios en Linear.
- Persistir metadata del cambio en estructura local versionable o regenerable.
- La metadata runtime debe vivir en `./.ai/workflows/sdd-linear/changes/`.
- Mantener secretos fuera de la configuración commiteada.
- Separar claramente `issue closed` de `feature done`.
- El core neutral recomendado debe vivir en `./.ai/workflows/sdd-linear/`.
- OpenCode debe ser el primer adaptador operativo porque gentle-ai ya soporta overlays, sync y perfiles SDD para ese agente.
- Para issues derivados, Engram es obligatorio; Linear se intenta siempre, con fallback manual tras 3 reintentos fallidos.
- Las evidencias mínimas de cierre en Fase 1 serán: PR URL, merge confirmado, notas de QA y validación de negocio.
- No se recomienda construir una TUI shell propia en Fase 1; primero debe reutilizarse la TUI/CLI de `gentle-ai` y, si hace falta, un bootstrap script interactivo liviano.
- El bootstrap shell script sí es recomendable en Fase 1 porque resuelve portabilidad práctica entre proyectos y máquinas sin introducir todavía una UI nueva.
- El bootstrap debe ser idempotente o, como mínimo, seguro ante reejecución con validaciones claras.

---

## 15. Risks & Assumptions

### Riesgos
- Complejidad extra del workflow si se automatiza demasiado temprano.
- Dependencia de credenciales y permisos correctos en Linear.
- Falsa sensación de cierre si las evidencias no se validan bien.

### Supuestos
- Linear será la fuente de verdad operativa del progreso.
- Engram seguirá siendo la fuente de verdad histórica/contextual.
- El equipo aceptará una disciplina de estados y gates explícitos.
- El ecosistema de agentes puede cambiar, por lo que la configuración debe sobrevivir a cambios de agente/adaptador.
- El workspace de Linear todavía no tiene todos los estados ideales, por lo que la Fase 1 deberá convivir con un mapping transitorio y la creación progresiva de estados.

---

## 16. Roadmap / Future Work

- Implementar `/sdd-feature-close`.
- Añadir dashboards o reportes de salud del workflow.
- Soportar múltiples templates por tipo de issue.
- Sincronizar links a PRs y QA de forma más automática.
- Agregar validación previa de configuración (`/sdd-config-validate`).
- Evaluar una TUI propia solo después de validar que `gentle-ai` TUI + bootstrap script no cubren el setup inicial.
- Implementar `scripts/bootstrap-sdd-linear.sh` con modo `dry-run` y checklist final.

---

## 17. Open Questions

- ¿Qué nombres exactos tendrán los estados iniciales de Linear a crear para el rollout?
- ¿Qué campos exactos deberá incluir el payload/prompt manual para fallback de creación de issues derivados?
- ¿El cierre de feature será manual al inicio o también automatizado?
- ¿Qué parte del bootstrap debe vivir en un script del proyecto y qué parte debe delegarse a `gentle-ai sync` / `skill-registry`?
