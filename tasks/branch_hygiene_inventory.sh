#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
NightLedger branch hygiene inventory

Usage:
  bash tasks/branch_hygiene_inventory.sh

This command is dry-run only.
No remote deletions are executed.
EOF
  exit 0
fi

git fetch origin main >/dev/null 2>&1 || true

timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Branch Hygiene Inventory Snapshot (${timestamp})"
echo
echo "Merged into origin/main"
merged_refs="$(git branch -r --merged origin/main --format='%(refname:short)' | sort)"
echo "${merged_refs}"
echo
echo "Not merged into origin/main"
not_merged_refs="$(git branch -r --no-merged origin/main --format='%(refname:short)' | sort)"
echo "${not_merged_refs}"
echo
echo "Deletion command template (operator-confirmed only)"
echo "Dry-run only. Review candidates before any manual deletion."

while IFS= read -r ref; do
  [[ -z "${ref}" ]] && continue
  case "${ref}" in
    origin/main|origin/HEAD|origin)
      continue
      ;;
  esac
  echo "git push origin --delete ${ref#origin/}"
done <<<"${merged_refs}"
