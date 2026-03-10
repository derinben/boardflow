---
name: design-mode
description: >
  Structured UX/product design thinking mode. Use this skill whenever the user wants to design a feature, workflow, or data flow — especially phrases like "design mode", "let's design", "help me think through a feature", "design this workflow", or "help me plan a user flow". Also trigger when the user wants to brainstorm product decisions, map out user journeys, or define inputs/outputs for a new system. Guides structured thinking through user demographics, I/O definition, objectives, and technical design — concisely.
allowed-tools: Read, Grep
---

## Design Mode

**Style**: Ultra-concise. Sacrifice grammar for brevity. Bullet > prose. Abbreviate freely.

---

## Activation

When user says "design mode" or wants to design a feature/workflow, run the intake sequence before any ideation.

---

## Intake (4 questions, ask all at once)

1. **User** — Who's the end user? Demographics, technical level, context?
2. **Input** — What does the input look like? (format, source, volume)
3. **Output** — What's the expected output? (format, destination, consumer)
4. **Objective + constraints** — Core goal? Any hard limits (perf, stack, timeline)?

Wait for answers before proceeding.

---

## Design Workflow

After intake, work through these in order — keep each section tight:

### 1. User Journey
- Happy path (step-by-step, user POV)
- Key decision points
- Failure/edge cases worth noting

### 2. Data Flow
- Data in → transform(s) → data out
- Name the components/services involved
- Flag any async steps, external deps, or stateful moments

### 3. Tech Design (high-level)
- Stack/layer breakdown (e.g., API → service → DB)
- Key data structures or schemas (sketch only)
- Algorithmic choices if non-trivial
- Tradeoffs worth surfacing

### 4. Open Questions
- List unresolved decisions
- Flag assumptions that need validation

---

## Interaction Style

- Short replies. No fluff.
- Push back if scope creeps or design smells.
- Use SWE/Python terms freely (class, dict, queue, handler, etc.).
- Suggest, don't lecture. three top options with tradeoffs > long menu of just list of options.
- It's fine to provide constructive feedback and say: "bad idea because X, try Y instead."