---
name: orchestrate
description: Subagent delegation and model-tiering policy for large or parallel work — main agent coordinates only, coding goes to sonnet subagents, docs/commits/chores to haiku, deep design to opus/fable. Use whenever starting a multi-part task, whenever the user says "서브에이전트 써서", "병렬로 해", "토큰 아껴", "너는 조율만 해", or when a task naturally splits into independent work streams.
---

# Orchestrate — Subagent & Model Tiering

The user runs long sessions on a budget and has repeatedly corrected the same two mistakes: the main (expensive) agent writing code itself, and background work starting before their question is answered. This policy prevents both.

## Role of the main agent

Coordinate, review, decide. Do **not** write implementation code in the main context when a subagent can. The main agent's context is the scarce resource — keep it for planning, reviewing subagent output, and talking to the user.

## Model tiering

| Work | Model |
|------|-------|
| Implementation coding, debugging | `sonnet` |
| Documentation, commit messages, log updates, terminal chores | `haiku` |
| Complex architecture/design decisions only | `opus` / `fable` (sparingly) |

Pass the model explicitly when spawning (`model` parameter). Default to the cheapest tier that can do the job; escalate only on failure.

## Answer first, then delegate

When the user's message contains a question **and** work to do: answer the question in your reply first, then kick off the background delegation. The user has explicitly complained about agents going silent into background work while their question hangs.

## Work splitting

- Split by independent streams (W1/W2/… pattern), each on its **own branch** so merges stay clean.
- Give each subagent a self-contained prompt: file paths, constraints, definition of done, and the relevant global rules (author flag, no push, conventions). Subagents don't inherit your conversation.
- Chain dependent work rather than parallelizing it — parallel agents editing the same files create conflicts that cost more than the parallelism saves.

## Monitoring and recovery

- You are notified when background tasks finish; don't poll.
- If a subagent stalls or dies, read its output, fix the prompt (usually missing context), and respawn — don't quietly take over the work in the main context, that defeats the tiering.
- Review every subagent's diff before integrating. Cheap models are fast but need the review pass.
