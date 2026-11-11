# Delegation

Use your judgment to spawn subagents when delegation improves speed, quality, or context management. This is a standing request to delegate suitable work; no separate request or confirmation is needed for each task. Prefer delegation for independent investigations, implementation tasks, and reviews. Handle small or tightly dependent tasks directly.

When the coding harness supports subagent model selection, explicitly prefer the cheapest available model capable of completing the task reliably. Use lightweight models for bounded searches, routine edits, and focused checks. Choose stronger models when complexity, ambiguity, risk, or inadequate results justify the additional cost. Do not inherit the parent model automatically when a cheaper suitable option is available.

Base model choices on the current harness's available models and documented cost tiers. Do not assume model names or selection mechanisms transfer between Codex and Claude Code. If costs are unknown, prefer the harness's documented lightweight tier; if model selection or tier information is unavailable, use its default. Respect explicit user model choices.

Give each subagent a bounded task, coordinate shared files, and review its results. Remain responsible for integration and verification. Respect explicit task restrictions, available tools, and higher-priority instructions.
