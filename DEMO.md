# Running the demo

Synthetic data only. Use the phone hotspot: venue Wi-Fi blocks the Atlas primary.

## Start

```bash
# 1. Agent Engine stack (local runtime, Atlas-backed memory and run state)
cd agent/agents/amma-harness && agentengine dev up          # playground :3000, oe :8100

# 2. Web app
cd web && nvm use && npm run dev                               # http://localhost:3100

# 3. Worker: runs go through the Agent Engine agent; unset AGENT_INVOKE_URL for the plain fallback
AGENT_INVOKE_URL=http://localhost:3000/invoke .venv/bin/python worker/run_worker.py
```

## Reset before each run

Under the hood → **Replay run** (about 70 s): rules back to v3, demo events cleared (test events kept),
Sep 12 uploaded again and paused on the smudged LDL.

## Script (2 minutes)

1. Family view: Blood sugar story and the March note.
2. New report banner: the smudged LDL `1?4` on the original photo. Click **It says 104**.
3. Ask about Amma: "Should we reduce her vitamin D dose?" → advice blocked, rewritten as a question.
4. Under the hood: v4-alt rejected and v4 promoted (numbers read live from `rules`).
5. Governance log: HELD, RELEASED, BLOCKED, REJECTED, PROMOTED; switch "Viewing as" to Home aide to show DENIED.

## Checks

`db/check_m1.py` … `db/check_m6.py`, `web/scripts/check-m4.mjs`, `web/scripts/check-m7.mjs`.
