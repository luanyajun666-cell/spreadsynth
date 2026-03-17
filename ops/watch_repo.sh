#!/usr/bin/env bash
set -euo pipefail

# Requires GH_TOKEN in environment (GitHub Actions provides via secrets.GITHUB_TOKEN)
if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "[watch] GH_TOKEN missing"
  exit 1
fi

MARKER="[Star-Reaper auto-watch]"
SINCE_UTC="$(date -u -d '20 minutes ago' +"%Y-%m-%dT%H:%M:%SZ")"

echo "[watch] scanning issues/PRs updated since $SINCE_UTC"

comment_issue_if_needed() {
  local number="$1"
  local author="$2"

  if [[ "$author" == "github-actions[bot]" ]]; then
    return
  fi

  local existing
  existing="$(gh issue view "$number" --json comments --jq '.comments[].body' 2>/dev/null || true)"
  if grep -q "$MARKER" <<<"$existing"; then
    return
  fi

  gh issue comment "$number" --body "$MARKER
⚡ Star-Reaper online.

收到你的问题，我会按以下节奏推进：
1) 先定位可复现路径
2) 再给出最小修复补丁
3) 最后补上验证步骤（避免回归）

If you can share logs / reproduction steps, I can return a precise patch path faster."
}

comment_pr_if_needed() {
  local number="$1"
  local author="$2"

  if [[ "$author" == "github-actions[bot]" ]]; then
    return
  fi

  local existing
  existing="$(gh pr view "$number" --json comments --jq '.comments[].body' 2>/dev/null || true)"
  if grep -q "$MARKER" <<<"$existing"; then
    return
  fi

  gh pr comment "$number" --body "$MARKER
🚀 Star-Reaper 已接管这条 PR 轨道。

我会重点检查：
- 评分逻辑是否可解释（D/T/C/A/K/F）
- 性能与可观测性是否可回放
- README 与行为是否一致（避免宣传与实现脱节）

Thanks for the contribution — review feedback will be structured and actionable."
}

# Issues
mapfile -t issue_rows < <(gh issue list --state open --search "updated:>=$SINCE_UTC" --json number,author --jq '.[] | "\(.number)|\(.author.login)"')
for row in "${issue_rows[@]:-}"; do
  [[ -z "$row" ]] && continue
  IFS='|' read -r num author <<<"$row"
  comment_issue_if_needed "$num" "$author"
done

# PRs
mapfile -t pr_rows < <(gh pr list --state open --search "updated:>=$SINCE_UTC" --json number,author --jq '.[] | "\(.number)|\(.author.login)"')
for row in "${pr_rows[@]:-}"; do
  [[ -z "$row" ]] && continue
  IFS='|' read -r num author <<<"$row"
  comment_pr_if_needed "$num" "$author"
done

echo "[watch] done"
