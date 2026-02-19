#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-$(pwd)}"
DOCS_DIR="${ROOT_DIR}/docs"

if [[ ! -d "${DOCS_DIR}" ]]; then
  echo "docs directory not found under: ${ROOT_DIR}" >&2
  exit 1
fi

declare -a files=()

if [[ -f "${DOCS_DIR}/diary.md" ]]; then
  files+=("${DOCS_DIR}/diary.md")
fi

while IFS= read -r path; do
  files+=("${path}")
done < <(find "${DOCS_DIR}/artifacts" -type f -name "*.md" 2>/dev/null | sort)

if [[ "${#files[@]}" -eq 0 ]]; then
  echo "No tracked progress artifacts found." >&2
  exit 1
fi

for file in "${files[@]}"; do
  if rg -qi '#(unknown|tbd)\b' "${file}"; then
    echo "Invalid issue placeholder found in ${file}: use numeric issue IDs." >&2
    exit 1
  fi

  if ! rg -q '#[0-9]+' "${file}"; then
    echo "Missing numeric issue reference in ${file}." >&2
    exit 1
  fi
done

echo "Validation passed: tracked progress artifacts reference valid issue IDs."
