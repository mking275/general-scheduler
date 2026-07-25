#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# VetAgent pilot — image build with deploy provenance (Pattern #4).
#
# Builds the api and voice-bridge images, stamping the resolved commit SHA into
# each (GIT_SHA build arg -> ENV -> /healthz). REFUSES to build from a tree that
# is not a clean, pushed reflection of origin/main, so a running revision always
# maps to a real, reviewable commit. Override ONLY for local testing:
#     ./deploy/pilot/build.sh --allow-dirty
#
# Usage:
#   ./deploy/pilot/build.sh [--allow-dirty] [--registry REG] [--tag TAG]
#                           [--api-only | --voice-only]
# Env:
#   REGISTRY   default: local (images tagged vetagent-<svc>:<tag>)
#   TAG        default: the short SHA
# ---------------------------------------------------------------------------
set -euo pipefail

# Repo root = two levels up from this script (deploy/pilot/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ALLOW_DIRTY=0
REGISTRY="${REGISTRY:-}"
TAG_OVERRIDE="${TAG:-}"
BUILD_API=1
BUILD_VOICE=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --allow-dirty) ALLOW_DIRTY=1; shift ;;
    --registry)    REGISTRY="$2"; shift 2 ;;
    --tag)         TAG_OVERRIDE="$2"; shift 2 ;;
    --api-only)    BUILD_VOICE=0; shift ;;
    --voice-only)  BUILD_API=0; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

git() { command git -C "${REPO_ROOT}" "$@"; }

GIT_SHA="$(git rev-parse HEAD)"
SHORT_SHA="$(git rev-parse --short HEAD)"

# ── Provenance guard ───────────────────────────────────────────────────────
if [[ "${ALLOW_DIRTY}" -eq 0 ]]; then
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "REFUSING: working tree is dirty. Commit/stash, or pass --allow-dirty for a local test build." >&2
    exit 1
  fi
  git fetch --quiet origin main || { echo "REFUSING: cannot fetch origin/main to verify sync." >&2; exit 1; }
  ORIGIN_MAIN="$(git rev-parse origin/main)"
  if [[ "${GIT_SHA}" != "${ORIGIN_MAIN}" ]]; then
    echo "REFUSING: HEAD (${SHORT_SHA}) != origin/main ($(git rev-parse --short origin/main))." >&2
    echo "         A provenance build must be from a pushed, review-merged commit. Use --allow-dirty to test locally." >&2
    exit 1
  fi
  echo "provenance OK: clean tree, HEAD == origin/main (${SHORT_SHA})"
else
  echo "WARNING: --allow-dirty set — building an UNVERIFIED tree (${SHORT_SHA}); do not deploy this image."
fi

TAG="${TAG_OVERRIDE:-${SHORT_SHA}}"
prefix=""
[[ -n "${REGISTRY}" ]] && prefix="${REGISTRY%/}/"

API_IMAGE="${prefix}vetagent-api:${TAG}"
VOICE_IMAGE="${prefix}vetagent-voice-bridge:${TAG}"

# Build context is the repo root; Dockerfiles live under deploy/pilot/.
if [[ "${BUILD_API}" -eq 1 ]]; then
  echo "building ${API_IMAGE} ..."
  command docker build \
    --build-arg "GIT_SHA=${GIT_SHA}" \
    -f "${SCRIPT_DIR}/Dockerfile.api" \
    -t "${API_IMAGE}" \
    "${REPO_ROOT}"
fi

if [[ "${BUILD_VOICE}" -eq 1 ]]; then
  echo "building ${VOICE_IMAGE} ..."
  command docker build \
    --build-arg "GIT_SHA=${GIT_SHA}" \
    -f "${SCRIPT_DIR}/Dockerfile.voice-bridge" \
    -t "${VOICE_IMAGE}" \
    "${REPO_ROOT}"
fi

echo "done. images:"
[[ "${BUILD_API}" -eq 1 ]]   && echo "  ${API_IMAGE}"
[[ "${BUILD_VOICE}" -eq 1 ]] && echo "  ${VOICE_IMAGE}"
echo "GIT_SHA=${GIT_SHA}"
