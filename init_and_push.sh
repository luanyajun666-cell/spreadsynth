#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./init_and_push.sh [repo-name] [public|private]
# Example:
#   ./init_and_push.sh spreadsynth public

REPO_NAME="${1:-spreadsynth}"
VISIBILITY="${2:-public}"
DESCRIPTION="${DESCRIPTION:-SpreadSynth - real-time signal arbitrage engine}"
MAIN_BRANCH="${MAIN_BRANCH:-main}"
TAG="${TAG:-v0.1.0}"

if [[ "$VISIBILITY" != "public" && "$VISIBILITY" != "private" ]]; then
  echo "[ERROR] VISIBILITY must be 'public' or 'private'"
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "[ERROR] git not found"
  exit 1
fi

GH_BIN="gh"
if ! command -v gh >/dev/null 2>&1; then
  if [[ -x "/c/Program Files/GitHub CLI/gh.exe" ]]; then
    GH_BIN="/c/Program Files/GitHub CLI/gh.exe"
  elif [[ -x "C:/Program Files/GitHub CLI/gh.exe" ]]; then
    GH_BIN="C:/Program Files/GitHub CLI/gh.exe"
  else
    echo "[ERROR] GitHub CLI (gh) not found. Install first: https://cli.github.com/"
    exit 1
  fi
fi

echo "[1/8] Ensuring this folder is an isolated git repo..."
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  TOP="$(git rev-parse --show-toplevel)"
  if [[ "$TOP" != "$PWD" && ! -d .git ]]; then
    echo "[INFO] Nested under another git repo. Initializing local .git here to isolate SpreadSynth."
    git init
  fi
else
  git init
fi

echo "[2/8] Checking gh auth status or GH_TOKEN..."
if [[ -n "${GH_TOKEN:-}" ]]; then
  echo "[INFO] GH_TOKEN detected; using token-based auth for gh commands."
else
  if ! "$GH_BIN" auth status >/dev/null 2>&1; then
    echo "[ERROR] gh is not authenticated. Run: \"$GH_BIN\" auth login"
    echo "        or export GH_TOKEN=<your_pat> and rerun this script."
    exit 1
  fi
fi

echo "[3/8] Verifying README visual placeholder guidance..."
if ! grep -q "Visuals are evolving" README.md; then
  echo "[WARN] README missing visual roadmap note."
fi
if ! grep -q "视觉素材占位说明" README.md; then
  echo "[WARN] README missing image placeholder section."
fi

echo "[4/8] Commit all files..."
git add -A
if git diff --cached --quiet; then
  echo "[INFO] No staged changes to commit."
else
  git commit -m "feat: initial SpreadSynth launch pack + scoring engine"
fi

echo "[5/8] Ensure branch: $MAIN_BRANCH"
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "$MAIN_BRANCH" ]]; then
  git branch -M "$MAIN_BRANCH"
fi

echo "[6/8] Create repo or attach remote..."
if ! "$GH_BIN" repo view "$REPO_NAME" >/dev/null 2>&1; then
  "$GH_BIN" repo create "$REPO_NAME" --"$VISIBILITY" --source=. --remote=origin --description "$DESCRIPTION"
else
  echo "[INFO] Repo '$REPO_NAME' already exists in current gh context."
  if ! git remote get-url origin >/dev/null 2>&1; then
    OWNER="$($GH_BIN api user -q .login)"
    git remote add origin "https://github.com/$OWNER/$REPO_NAME.git"
  fi
fi

echo "[7/8] Push branch + tag..."
git push -u origin "$MAIN_BRANCH"
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "[INFO] Local tag $TAG already exists."
else
  git tag -a "$TAG" -m "First release: SpreadSynth launch pack + scoring engine"
fi
git push origin "$TAG" || true

echo "[8/8] Create GitHub Release..."
if ! "$GH_BIN" release view "$TAG" >/dev/null 2>&1; then
  "$GH_BIN" release create "$TAG" --title "$TAG" --notes "Initial public release of SpreadSynth."
else
  echo "[INFO] Release $TAG already exists."
fi

echo "✅ Done. Repo published and first tag/release attempted."
