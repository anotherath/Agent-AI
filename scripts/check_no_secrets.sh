#!/usr/bin/env bash
# Fail if staged/tracked files look like they contain real secrets.
# Usage: ./scripts/check_no_secrets.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RED=$'\033[0;31m'
GRN=$'\033[0;32m'
YLW=$'\033[0;33m'
NC=$'\033[0m'

fail=0

echo "${YLW}Checking secret hygiene…${NC}"

# 1) .env must never be tracked
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    echo "${RED}ERROR: .env is tracked by git. Remove it: git rm --cached .env${NC}"
    fail=1
  fi
  # Files to scan: staged if any, else tracked
  if git diff --cached --name-only | grep -q .; then
    mapfile -t FILES < <(git diff --cached --name-only --diff-filter=ACMR)
  else
    mapfile -t FILES < <(git ls-files)
  fi
else
  echo "${YLW}Not a git repo yet — scanning working tree (excluding .venv/.git).${NC}"
  mapfile -t FILES < <(find . -type f \
    ! -path './.venv/*' \
    ! -path './.git/*' \
    ! -path './node_modules/*' \
    ! -name '.env' \
    ! -name '.env.*' \
    -print)
fi

# 2) Forbidden filenames in the file list
for f in "${FILES[@]:-}"; do
  base="$(basename "$f")"
  case "$base" in
    .env|.env.local|.env.production|.env.development)
      echo "${RED}ERROR: env file in commit set: $f${NC}"
      fail=1
      ;;
    credentials.json|service-account.json)
      echo "${RED}ERROR: credential file in commit set: $f${NC}"
      fail=1
      ;;
  esac
  case "$f" in
    *.pem|*.p12|*.pfx)
      echo "${RED}ERROR: key/cert file in commit set: $f${NC}"
      fail=1
      ;;
  esac
done

# 3) Content patterns (skip .env.example placeholders)
PATTERNS=(
  'sk-[a-zA-Z0-9]{20,}'
  'tvly-[a-zA-Z0-9_]{20,}'
  'CG-[a-zA-Z0-9]{20,}'
  '-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----'
  'AKIA[0-9A-Z]{16}'
)

for f in "${FILES[@]:-}"; do
  [[ -f "$f" ]] || continue
  case "$f" in
    .env.example|.env.*.example|scripts/check_no_secrets.sh) continue ;;
    *.md) continue ;;  # docs may mention sk-your-key-here style placeholders in prose
  esac
  # Skip binary-ish
  if file -b --mime-encoding "$f" 2>/dev/null | grep -qi binary; then
    continue
  fi
  for pat in "${PATTERNS[@]}"; do
    if grep -EIq "$pat" "$f" 2>/dev/null; then
      # Allow obvious placeholders
      if grep -EIq 'your-key-here|sk-xxxxxxxx|tvly-your-key|CG-test-key|placeholder|example' "$f"; then
        # Still flag if a line looks like a real long key without placeholder words
        if grep -En "$pat" "$f" | grep -Eiv 'your-key-here|sk-x{8,}|tvly-your-key|CG-test-key|placeholder|example' | grep -q .; then
          echo "${RED}ERROR: possible secret in $f (pattern: $pat)${NC}"
          grep -En "$pat" "$f" | head -3
          fail=1
        fi
      else
        echo "${RED}ERROR: possible secret in $f (pattern: $pat)${NC}"
        grep -En "$pat" "$f" | head -3
        fail=1
      fi
    fi
  done
done

if [[ "$fail" -ne 0 ]]; then
  echo "${RED}Secret check FAILED. Fix before pushing to GitHub.${NC}"
  exit 1
fi

echo "${GRN}OK — no obvious secrets in scanned files.${NC}"
echo "${YLW}Reminder: keep real keys only in local .env (gitignored). Rotate keys if they were ever committed or pasted publicly.${NC}"
