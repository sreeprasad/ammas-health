Read PLAN.md. It is the engineering plan for a hackathon project:
a family health record on MongoDB Atlas + Atlas Agent Engine.
design/Concept4.dc.html is the UI mockup for both screens (Family view and Under the hood).
Match its layout, colors and copy when building M4 and M7.

Rules:
- Work one milestone at a time, in order (M1 → M7). M0 is done by me.
- Before starting a milestone, list its steps and the files you'll touch, then wait for my OK.
- After each milestone, run its "Done when" check and show me the result. Do not start the next until it passes.
- Atlas Agent Engine is a public preview. Use only the documented APIs:
  agentengine CLI, and the Python package agentic_platform_memory
  (Memory, MemoryRequestContext, save_semantic, save_episode,
  save_taxonomic, save_procedure, build_context). If you need anything
  else, ask me to check the docs. Never invent an API.
- Always bind memory with an explicit user_id="amma" (standalone memory SDK).
- Synthetic data only. Never add real patient data.
- The agent's DB user must never be able to read the eval_vault database.
- Keep secrets in .env, never in code.
- Commit after each milestone with a message naming the milestone.

Start with M1.
