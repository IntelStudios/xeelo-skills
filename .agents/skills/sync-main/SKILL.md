---
name: sync-main
description: >-
  Start or stop an hourly check of origin/main on this xeelo-skills clone and
  fast-forward pull when there are new commits. Use when the user invokes
  /sync-main, asks to watch/sync/pull the KB main branch on a schedule, or
  wants a background job that keeps local main current.
disable-model-invocation: true
---

# Sync xeelo-skills `main`

Keep this clone’s **`main`** aligned with **`origin/main`**. Default cadence: **every hour**. This is git on the public KB repo — not a Xeelo site change loop and not `/download-db`.

## When

- User invokes **`/sync-main`**, or asks to regularly check/pull/`fetch` **xeelo-skills `main`**
- **Stop** when they ask to stop the hourly job / unwatch `main`

Do **not** start a second copy if a matching loop is already running.

## Start

1. Confirm the git root is this xeelo-skills repo (`origin` points at the public KB).
2. Interval: **1 hour** unless the user names another (`30m`, `2h`, …).
3. **Once immediately:** `git fetch origin`. If `HEAD` is `main`, the tree is clean, and `main` is behind `origin/main`, `git pull --ff-only origin main`. If already up to date, say so (one line). If the pull brought commits, summarize them in chat the same way as **On PULLED_MAIN wake** (`git log --reverse --format='%h %s' OLD..HEAD` before or after the pull).
4. Check existing terminals for `LOOP_PULL_MAIN_STARTED` / “pull main if new commits”. If one is running, report its PID and **do not** start another.
5. Arm **one** background shell (do not wake the agent every tick — the shell does the git work):

```bash
echo "LOOP_PULL_MAIN_STARTED interval=<seconds>s repo=$(pwd) pid=$$"
while true; do
  sleep <seconds>
  git fetch origin
  remote=$(git rev-parse origin/main 2>/dev/null) || continue
  local=$(git rev-parse refs/heads/main 2>/dev/null) || continue
  if [ "$local" = "$remote" ]; then
    continue
  fi
  log=$(git log --reverse --format='%h %s' "$local..$remote")
  n=$(printf '%s\n' "$log" | grep -c .)
  branch=$(git branch --show-current)
  if [ "$branch" = "main" ]; then
    if [ -n "$(git status --porcelain)" ]; then
      echo "SKIP_PULL_MAIN dirty working tree"
      continue
    fi
    if git pull --ff-only origin main; then
      echo "PULLED_MAIN n=$n from=$(git rev-parse --short "$local") to=$(git rev-parse --short "$remote")"
      echo "$log"
    else
      echo "SKIP_PULL_MAIN pull failed"
    fi
  else
    if git merge-base --is-ancestor refs/heads/main origin/main; then
      git update-ref refs/heads/main "$remote"
      echo "PULLED_MAIN n=$n from=$(git rev-parse --short "$local") to=$(git rev-parse --short "$remote") (stayed on $branch)"
      echo "$log"
    else
      echo "SKIP_PULL_MAIN local main not fast-forward"
    fi
  fi
done
```

6. Notify on output matching `PULLED_MAIN` (one sentinel line, then the commit list — so the agent wakes **once** per successful update). First `sleep` is the full interval — the immediate pull in step 3 must not double-run.
7. Confirm: interval, that you already fetched/pulled once, PID, when the next check is, and that the job runs until they ask to stop.

## On PULLED_MAIN wake

The notification includes a path to the shell output, not a prompt. Read the `PULLED_MAIN` line and the `%h %s` list immediately after it.

Write a short chat summary **in the user’s language** of what landed on `main` (from the commit subjects). Do not dump the raw git log.

- **1–3 commits:** bullets with the subjects.
- **More:** group thematically from the subjects.
- **~20+:** themes and the count only (`n=` on the sentinel).

Do not re-run `git log` when the list is in the output. Exception: the output is truncated or empty — then `git log --reverse --format='%h %s' FROM..TO` using the SHAs on the sentinel.

`SKIP_PULL_MAIN` does not notify.

## Rules

- **Fast-forward only.** Never `--force`, never rebase, never skip hooks.
- On **`main`** with a dirty tree: skip (log `SKIP_PULL_MAIN dirty working tree`).
- On **another branch**: fast-forward the local `main` ref only; **do not** checkout `main`.
- If `main` cannot fast-forward to `origin/main`: skip and say so on the next user-visible update (do not merge).
- Session-scoped: the loop dies with the terminal/session. LaunchAgent / cron **only** if the user asks for survival across restarts — do not invent a plist into the public KB.

## Stop

Find the running loop (`LOOP_PULL_MAIN_STARTED` / same command). Kill that PID. Await the shell so a stale completion does not retrigger. Do not start another loop. Confirm it stopped.

## Output

- Start: interval, PID, result of the immediate fetch/pull (including a commit summary if anything was pulled), next tick.
- Later ticks: only when `PULLED_MAIN` (new commits) — summarize those commits in chat — or if the user asks for status.
- Stop: stopped, and why.
