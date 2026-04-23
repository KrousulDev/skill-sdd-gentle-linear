#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bootstrap-sdd-linear.sh <target-path> [--source-repo <local-path>] [--agent <opencode|auto>] [--force] [--dry-run] [--yes]

Notes:
  - This Fase 1 bootstrap syncs managed project paths from a local source repo.
  - Remote git URLs are intentionally out of scope for this script.
  - Secrets are never copied into repo files; configure credentials after bootstrap.
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

TARGET_PATH=""
SOURCE_REPO=""
AGENT="opencode"
FORCE=0
DRY_RUN=0
ASSUME_YES=0

TARGET_PATH="$1"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source-repo)
      [[ $# -ge 2 ]] || { echo "Missing value for --source-repo" >&2; exit 1; }
      SOURCE_REPO="$2"
      shift 2
      ;;
    --agent)
      [[ $# -ge 2 ]] || { echo "Missing value for --agent" >&2; exit 1; }
      AGENT="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --yes)
      ASSUME_YES=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_SOURCE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_ROOT="$DEFAULT_SOURCE_ROOT"

if [[ -n "$SOURCE_REPO" ]]; then
  if [[ "$SOURCE_REPO" =~ ^https?:// ]] || [[ "$SOURCE_REPO" =~ ^git@ ]]; then
    echo "Remote source repositories are not supported in this Fase 1 bootstrap. Provide a local path instead." >&2
    exit 1
  fi
  SOURCE_ROOT="$(cd "$SOURCE_REPO" && pwd)"
fi

case "$AGENT" in
  auto)
    AGENT="opencode"
    ;;
  opencode)
    ;;
  *)
    echo "Unsupported agent: $AGENT. Fase 1 bootstrap supports only opencode/auto." >&2
    exit 1
    ;;
esac

TARGET_ROOT="$(mkdir -p "$TARGET_PATH" && cd "$TARGET_PATH" && pwd)"

if [[ $ASSUME_YES -ne 1 && $DRY_RUN -ne 1 ]]; then
  echo "Bootstrap source: $SOURCE_ROOT"
  echo "Bootstrap target: $TARGET_ROOT"
  printf 'Continue with managed path sync? [y/N] '
  read -r reply
  if [[ ! "$reply" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Aborted."
    exit 1
  fi
fi

CREATED=0
UPDATED=0
SKIPPED=0
declare -a CREATED_PATHS=()
declare -a UPDATED_PATHS=()
declare -a SKIPPED_PATHS=()

record_action() {
  local action="$1"
  local path="$2"
  case "$action" in
    created)
      CREATED=$((CREATED + 1))
      CREATED_PATHS+=("$path")
      ;;
    updated)
      UPDATED=$((UPDATED + 1))
      UPDATED_PATHS+=("$path")
      ;;
    skipped)
      SKIPPED=$((SKIPPED + 1))
      SKIPPED_PATHS+=("$path")
      ;;
  esac
}

copy_managed_file() {
  local relative_path="$1"
  local source_file="$SOURCE_ROOT/$relative_path"
  local target_file="$TARGET_ROOT/$relative_path"

  if [[ ! -f "$source_file" ]]; then
    echo "Missing managed source file: $source_file" >&2
    exit 1
  fi

  if [[ ! -e "$target_file" ]]; then
    record_action "created" "$relative_path"
    if [[ $DRY_RUN -eq 0 ]]; then
      mkdir -p "$(dirname "$target_file")"
      cp "$source_file" "$target_file"
    fi
    return
  fi

  if cmp -s "$source_file" "$target_file"; then
    record_action "skipped" "$relative_path"
    return
  fi

  if [[ $FORCE -eq 1 ]]; then
    record_action "updated" "$relative_path"
    if [[ $DRY_RUN -eq 0 ]]; then
      mkdir -p "$(dirname "$target_file")"
      cp "$source_file" "$target_file"
    fi
  else
    record_action "skipped" "$relative_path"
  fi
}

MANAGED_FILES=(
  ".ai/workflows/sdd-linear/config.json"
  ".ai/workflows/sdd-linear/state-map.json"
  ".ai/workflows/sdd-linear/contracts/change-metadata.schema.json"
  ".ai/workflows/sdd-linear/contracts/derived-issue.schema.json"
  ".ai/workflows/sdd-linear/contracts/archive-evidence.schema.json"
  ".ai/workflows/sdd-linear/templates/archive-comment.md"
  ".ai/workflows/sdd-linear/templates/manual-derived-issue.md"
  ".ai/workflows/sdd-linear/bin/sdd_linear_core.py"
  ".ai/workflows/sdd-linear/changes/.gitkeep"
  ".opencode/commands/sdd-linear/sdd-new.md"
  ".opencode/commands/sdd-linear/sdd-status.md"
  ".opencode/commands/sdd-linear/sdd-log-issue.md"
  ".opencode/commands/sdd-linear/sdd-archive.md"
  ".atl/skills/sdd-linear-flow/SKILL.md"
)

for relative_path in "${MANAGED_FILES[@]}"; do
  if [[ "$relative_path" == .atl/* && "$AGENT" != "opencode" ]]; then
    continue
  fi
  copy_managed_file "$relative_path"
done

print_paths() {
  local heading="$1"
  local count="$2"
  shift 2
  local -a paths=("$@")
  echo "$heading"
  if [[ "$count" -eq 0 ]]; then
    echo "  - none"
    return
  fi
  local path
  for path in "${paths[@]}"; do
    echo "  - $path"
  done
}

echo ""
echo "SDD Linear bootstrap summary"
echo "  source: $SOURCE_ROOT"
echo "  target: $TARGET_ROOT"
echo "  mode: $([[ $DRY_RUN -eq 1 ]] && echo dry-run || echo apply)"
echo "  agent: $AGENT"
echo "  created: $CREATED"
echo "  updated: $UPDATED"
echo "  skipped: $SKIPPED"
echo ""
print_paths "Created paths:" "$CREATED" "${CREATED_PATHS[@]:-}"
print_paths "Updated paths:" "$UPDATED" "${UPDATED_PATHS[@]:-}"
print_paths "Skipped paths:" "$SKIPPED" "${SKIPPED_PATHS[@]:-}"
echo ""
echo "Next steps:"
echo "  1. Configure Linear and Engram credentials outside the repo (env vars or local secret manager)."
echo "  2. Run your normal agent sync/refresh step so project-local commands and skills are discovered."
echo "  3. Verify state mapping and templates before first real /sdd-new execution."
echo "  4. Do NOT store API tokens, cookies, or workspace secrets in tracked repo files."
