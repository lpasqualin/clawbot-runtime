# deep-debugging

Systematic, evidence-based debugging methodology for software developers. No guessing, no blind fixes — prove the root cause first, then solve it.

## The Problem This Solves

Most developers debug by instinct: "Let me try X and see if it helps." This leads to:
- Multiple fixes applied simultaneously (you don't know which one worked)
- Hours wasted on symptoms instead of root causes
- The same bug appearing again because it was never truly understood

## The Solution

A 4-phase protocol that forces evidence-based debugging:
1. **Gather Evidence** — observe only, don't touch anything
2. **Form a Hypothesis** — specific and testable
3. **Binary Search** — narrow down the bug systematically
4. **Fix** — minimal, targeted fix with verification

## What's Included

- `SKILL.md` — Core debugging protocol (language-agnostic)
- `references/nestjs.md` — NestJS + Next.js specific debugging
- `references/patterns.md` — Real bug patterns with root cause analysis

## Who This Is For

Backend and full-stack developers who want to debug systematically instead of randomly. Especially useful for:
- Auth / session bugs
- API issues (401, 403, 500)
- Cross-origin / CORS problems
- Bugs that return after being "fixed"
