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
3. **Once immediately:** `git fetch origin`. If `HEAD` is `main`, the tree is clean, and `main` is behind `origin/main`, `git pull --ff-only origin main`. If already up to date, say so (one line).
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
  branch=$(git branch --show-current)
  if [ "$branch" = "main" ]; then
    if [ -n "$(git status --porcelain)" ]; then
      echo "SKIP_PULL_MAIN dirty working tree"
      continue
    fi
    if git pull --ff-only origin main; then
      echo "PULLED_MAIN $(git log -1 --oneline)"
    else
      echo "SKIP_PULL_MAIN pull failed"
    fi
  else
    if git merge-base --is-ancestor refs/heads/main origin/main; then
      git update-ref refs/heads/main "$remote"
      echo "PULLED_MAIN updated local main to $(git rev-parse --short refs/heads/main) (stayed on $branch)"
    else
      echo "SKIP_PULL_MAIN local main not fast-forward"
    fi
  fi
done
```

6. Notify on output matching `PULLED_MAIN` (so a successful update is visible). First `sleep` is the full interval — the immediate pull in step 3 must not double-run.
7. Confirm: interval, that you already fetched/pulled once, PID, when the next check is, and that the job runs until they ask to stop.

## Rules

- **Fast-forward only.** Never `--force`, never rebase, never skip hooks.
- On **`main`** with a dirty tree: skip (log `SKIP_PULL_MAIN dirty working tree`).
- On **another branch**: fast-forward the local `main` ref only; **do not** checkout `main`.
- If `main` cannot fast-forward to `origin/main`: skip and say so on the next user-visible update (do not merge).
- Session-scoped: the loop dies with the terminal/session. LaunchAgent / cron **only** if the user asks for survival across restarts — do not invent a plist into the public KB.

## Stop

Find the running loop (`LOOP_PULL_MAIN_STARTED` / same command). Kill that PID. Await the shell so a stale completion does not retrigger. Do not start another loop. Confirm it stopped.

## Output

- Start: interval, PID, result of the immediate fetch/pull, next tick.
- Later ticks: only when `PULLED_MAIN` (new commits) or if the user asks for status.
- Stop: stopped, and why.
