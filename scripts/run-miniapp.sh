#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
COMPOSE_DIR="${REPO_ROOT}/infra/compose"

DEFAULT_STACK=(
  "miniapp.compose.yaml"
  "miniapp.runtime.yml"
  "miniapp.stack.yml"
  "miniapp.readiness.override.yml"
  "miniapp.final.override.yml"
)

ENV_FILE="${COMPOSE_DIR}/.env.miniapp"
ENV_EXAMPLE="${COMPOSE_DIR}/env.miniapp.example"

usage() {
  cat <<'USAGE'
Usage: run-miniapp.sh <command> [args...]

Commands:
  pull [service...]      Pull images for the stack (respects SERVICES var)
  up [args...]           Start services (defaults to --wait -d)
  down [args...]         Stop services
  logs [args...]         Tail logs (defaults to -f)
  ps [args...]           Show service status
  config                 Render merged compose configuration
  exec <svc> <cmd...>    Run a command inside a service container

Environment variables:
  MINIAPP_EXTRA_FILES   Colon-separated list of extra compose files (optional)
  MINIAPP_NO_WAIT       If set to non-empty, skips --wait during `up`
  SERVICES              Space-separated list of services to target (optional)
USAGE
}

detect_compose_files() {
  local -a files=()

  for candidate in "${DEFAULT_STACK[@]}"; do
    if [[ -f "${COMPOSE_DIR}/${candidate}" ]]; then
      files+=("${COMPOSE_DIR}/${candidate}")
    fi
  done

  if [[ -n "${MINIAPP_EXTRA_FILES:-}" ]]; then
    IFS=':' read -r -a extra_files <<< "${MINIAPP_EXTRA_FILES}"
    for extra in "${extra_files[@]}"; do
      [[ -z "${extra}" ]] && continue
      local resolved=""
      if [[ "${extra}" = /* && -f "${extra}" ]]; then
        resolved="${extra}"
      elif [[ -f "${COMPOSE_DIR}/${extra}" ]]; then
        resolved="${COMPOSE_DIR}/${extra}"
      elif [[ -f "${REPO_ROOT}/${extra}" ]]; then
        resolved="${REPO_ROOT}/${extra}"
      elif [[ -f "${extra}" ]]; then
        resolved="$(cd "$(dirname "${extra}")" && pwd)/$(basename "${extra}")"
      fi

      if [[ -n "${resolved}" && -f "${resolved}" ]]; then
        files+=("${resolved}")
      else
        printf 'Warning: extra compose file not found: %s\n' "${extra}" >&2
      fi
    done
  fi

  if [[ ${#files[@]} -eq 0 ]]; then
    printf 'No compose files detected in %s\n' "${COMPOSE_DIR}" >&2
    exit 1
  fi

  printf '%s\0' "${files[@]}"
}

ensure_env_file() {
  if [[ -f "${ENV_FILE}" ]]; then
    return
  fi

  if [[ -f "${ENV_EXAMPLE}" ]]; then
    printf 'Warning: %s not found. Copying from example...\n' "${ENV_FILE#${REPO_ROOT}/}"
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
    printf 'Created %s. Please review and update secrets before retrying.\n' "${ENV_FILE#${REPO_ROOT}/}" >&2
  fi

  printf 'Missing environment file: %s\n' "${ENV_FILE#${REPO_ROOT}/}" >&2
  printf 'Provide secrets at that path before running the miniapp stack.\n' >&2
  exit 1
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    printf 'docker command not found; install Docker before proceeding.\n' >&2
    exit 1
  fi
}

build_compose_command() {
  local -a compose_args=()
  IFS=$'\0' read -r -d '' -a compose_files < <(detect_compose_files)

  compose_args+=(--project-name miniapp)
  compose_args+=(--env-file "${ENV_FILE}")

  for file in "${compose_files[@]}"; do
    compose_args+=(-f "${file}")
  done

  printf '%s\0' "${compose_args[@]}"
}

run_compose() {
  local command=$1
  shift || true

  IFS=$'\0' read -r -d '' -a compose_args < <(build_compose_command)
  local -a docker_cmd=(docker compose "${compose_args[@]}" "${command}")
  local -a log_cmd=(docker compose "${compose_args[@]}" "${command}")

  if [[ "${command}" = "logs" && "$#" -eq 0 ]]; then
    set -- -f
  fi

  if [[ "${command}" = "up" ]]; then
    local -a default_flags=(-d)
    if [[ -z "${MINIAPP_NO_WAIT:-}" ]]; then
      default_flags+=(--wait)
    fi
    docker_cmd+=("${default_flags[@]}")
    log_cmd+=("${default_flags[@]}")
  fi

  if [[ "${command}" != "exec" && -n "${SERVICES:-}" ]]; then
    set -- "$@" ${SERVICES}
  fi

  docker_cmd+=("$@")
  log_cmd+=("$@")

  printf 'Using compose files:\n' >&2
  for arg in "${compose_args[@]}"; do
    if [[ "${arg}" == "-f" ]]; then
      continue
    fi
    if [[ "${arg}" =~ ^/.+\.ya?ml$ ]]; then
      printf '  - %s\n' "${arg#${REPO_ROOT}/}" >&2
    fi
  done

  printf 'Running:' >&2
  for token in "${log_cmd[@]}"; do
    printf ' %q' "${token}" >&2
  done
  printf '\n' >&2
  exec "${docker_cmd[@]}"
}

main() {
  if [[ $# -eq 0 ]]; then
    usage >&2
    exit 2
  fi

  require_docker
  ensure_env_file

  local command=$1
  shift || true

  case "${command}" in
    pull|up|down|logs|ps|config|exec)
      run_compose "${command}" "$@"
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      printf 'Unknown command: %s\n\n' "${command}" >&2
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"

