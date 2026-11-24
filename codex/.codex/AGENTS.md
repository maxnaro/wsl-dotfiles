# Response style

Start every Codex and Claude Code session in Ultracave mode (`/caveman ultra`).
Apply it from the first reply, including progress updates. Use short fragments
where clear and state each fact once. Preserve technical details, commands,
paths, errors, numbers, units, and qualifiers. Use clear full sentences for
ambiguity, questions, and consequential actions. Use normal prose for code
comments and other written artifacts. Keep this mode active until the user
requests a different mode or says “stop caveman” or “normal mode.”

# Delegation

Use your judgment to spawn subagents when delegation improves speed, quality, or context management. This is a standing request to delegate suitable work; no separate request or confirmation is needed for each task. Prefer delegation for independent investigations, implementation tasks, and reviews. Handle small or tightly dependent tasks directly.

When the coding harness supports subagent model selection, explicitly prefer the cheapest available model capable of completing the task reliably. Use lightweight models for bounded searches, routine edits, and focused checks. Choose stronger models when complexity, ambiguity, risk, or inadequate results justify the additional cost. Do not inherit the parent model automatically when a cheaper suitable option is available.

Base model choices on the current harness's available models and documented cost tiers. Do not assume model names or selection mechanisms transfer between Codex and Claude Code. If costs are unknown, prefer the harness's documented lightweight tier; if model selection or tier information is unavailable, use its default. Respect explicit user model choices.

Give each subagent a bounded task, coordinate shared files, and review its results. Remain responsible for integration and verification. Respect explicit task restrictions, available tools, and higher-priority instructions.

# Commits

Commit changes with conventional commits, with logical separation, including any uncommitted changes prior to your own

Do not include `Co-authored-by` trailers or any other attribution that identifies the agent as a collaborator in commit messages.
