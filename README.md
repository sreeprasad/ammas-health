# Amma's Health

**A family health record that reads lab reports, remembers them for months, learns from corrections, and proves every step.**
Built for the MongoDB *Harness Engineering & Model Wrangling* hackathon (SF Tech Week 2026) on **MongoDB Atlas** and **Atlas Agent Engine**.

> All data in this repo is synthetic. "Amma K." and "Amrut Clinic" are fictional. No real patient data was used.

**Demo video:** https://www.youtube.com/watch?v=AMICUd4mt9k

---

## The problem

My mother has dozens of lab reports across many hospital visits. Our family couldn't answer simple questions:

- Is her blood sugar getting worse since March?
- What did the doctor ask us to watch?
- What should we ask at the next visit?

Generic AI tools can summarize one report, but a family needs something that **remembers for months**, **never guesses on a health value**, **gets better when we correct it**, and **never gives treatment advice**. Those are exactly the problems that stall agents in production: memory, reliability, governance and security.

## What it does

Two screens share one live run state.

**Family view**
- Upload a photo of a lab report; the agent reads every value.
- A body map shows each area of her health: rising, low, improving or steady.
- Trend charts show the normal range, and every point links back to the original report page.
- A grid shows every report side by side.
- Questions are prepared for the next doctor visit.
- "Ask about Amma": family questions are answered from her record, and treatment advice is blocked.

**Under the hood**
- The agent pipeline, with each step's status and trace.
- Memory writes, labelled by type.
- The learning check, which tests every new rule before it goes live.
- The follow-up watcher.
- The governance log.

### 1. It never guesses: a durable pause
The Verifier checks every value against her history and the printed reference range. On the Sep 12 report, one LDL digit is smudged: it could be 104 or 184. A jump to 184 would break her steady trend, so **the run pauses instead of guessing**.

The pause is checkpointed in Atlas and survives a container restart. When a family member confirms the value, a change stream resumes the run from that checkpoint, without re-reading the photo.

### 2. It remembers: all four Agent Engine memory types
Memory is scoped to the patient with the standalone `agentic_platform_memory` SDK and an explicit `user_id`, so local and cloud runs share one scope.

| Memory type | What we store |
|---|---|
| **Semantic** | Her current value for each test (history is kept in Atlas) |
| **Episodic** | One episode per visit, including the doctor's note |
| **Taxonomic** | A shared dictionary of test names: `HGB` → Hemoglobin, `Glucose (F)` → Fasting glucose |
| **Procedural** | Versioned rules for reading this clinic's report layouts |

Retrieval goes through `build_context` with Voyage AI. A policy blocks any **unverified** value from being written to memory.

### 3. It learns, behind a gate
A family member's correction becomes a candidate reading rule. Before any rule goes live:

1. An eval runner re-reads **22 earlier reports**.
2. It scores each candidate against **locked answers** in a separate `eval_vault` database. The agent's database user cannot read that database.
3. A rule is promoted only if no value that was previously read correctly turns wrong.

| Rule | Result | Gate |
|---|---|---|
| v3 (live before) | baseline | — |
| v4-alt: "snap smudged digits to her trend" (proposed by the agent) | 1 regression | **Rejected** |
| v4: "smudged digit + big jump → ask a person" (from the family's answer) | **380 / 380**, 0 regressions | **Promoted** |

### 4. It works across weeks
The Watcher pulls follow-ups from the doctor's notes ("recheck HbA1c in 2 months") and tracks them across months. It flags any that never happened and adds them to the next visit's questions.

### 5. It's governed and secure
- **Never advises treatment.** A policy checks every reply. A question like "Should we reduce her vitamin D dose?" is blocked and rewritten as a question for her doctor.
- **Family scopes.** Family members see everything; the home aide sees the medication schedule only. Other requests are denied.
- **Least privilege.** Separate database users; the cloud agent cannot read `eval_vault`.
- **Encrypted doctor notes**, with the key held as a workspace-scoped secret.
- **Audit log.** Every HELD, BLOCKED, DENIED and REJECTED action is recorded with the identity that caused it.

## MongoDB features used

| Feature | How we use it |
|---|---|
| **Atlas Agent Engine runtime** | The harness agent is deployed to the cloud (8 replicas) with a durable pause and resume |
| **Agent Engine memory** | All four types, scoped per patient |
| **Voyage AI retrieval** | Context for every agent step through `build_context` |
| **Atlas collections** | Reports, values, runs (a checkpoint after every step), rules, follow-ups, members, audit log |
| **Change streams** | A new upload starts a run; a family member's answer resumes a paused one |
| **GridFS** | Original report photos, so every value links to its source |
| **Database users and roles** | Least-privilege access; the answer vault is unreadable to the agent |

## What we learned about Agent Engine

- **Memory scope on deployed agents.** A deployed agent called through a service account uses the service account's identity for memory, not the `user_id` we pass. We used the standalone memory SDK with an explicit `user_id` instead.
- **Traces are UI-only.** There is no documented traces API, so each run keeps its own step log and links to its Agent Engine session.
- **`agentengine atlas setup` grants broad access by default.** We replaced it with narrower database users.

