---
name: orchestrate
description: Coordinate explicitly requested subagents or parallel work while keeping responsibilities and edits isolated. Use when the user asks to use subagents, delegate work, run tasks in parallel, or have the main agent coordinate only.
---

# Orchestrate Agents

Use subagents only when the user explicitly requests delegation, parallel
agents, or an applicable higher-priority instruction requires them.

## Main-agent role

Own the user conversation, task decomposition, decisions, integration, and
final verification. Answer direct questions before starting background work.

## Split work safely

- Split by independent deliverables or non-overlapping file ownership.
- Chain dependent work instead of running it concurrently.
- Give every agent a bounded prompt with inputs, paths, constraints, expected
  output, validation, and prohibited actions.
- Do not pass hidden conclusions or the intended answer when the agent is
  acting as an independent reviewer.
- Assume agents may share a filesystem. Do not have concurrent agents switch
  branches or edit the same files unless the host provides isolated worktrees.

## Model selection

Use the host's default model unless the user or applicable configuration asks
for a particular model or tier. Prefer a balanced model for routine bounded
work and a frontier reasoning model only for genuinely difficult design or
debugging. Do not use model names from another agent platform.

## Monitor and integrate

- Review every agent result and diff before integrating it.
- Check that claimed tests actually ran and that edits stayed in scope.
- If an agent stalls, provide the missing context or re-scope the task; do not
  duplicate its work concurrently.
- Resolve overlaps in the main context and run final end-to-end validation.

Report the integrated outcome, not a transcript of agent activity.
