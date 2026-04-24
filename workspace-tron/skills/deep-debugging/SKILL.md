---
name: deep-debugging
description: "Systematic, evidence-based debugging methodology. No guessing, no blind fixes — prove the cause first, then solve it. Use when: (1) a bug persists after the first fix attempt, (2) you're tempted to 'just try something', (3) you can't reproduce the issue consistently, (4) debugging auth/session/API issues, (5) the error message is vague or missing. Trigger phrases: 'debug', 'debugging', 'why doesn't X work', 'still broken', 'can't figure out', 'investigate this bug'."
---

# Deep Debugging

**No blind fixes. No guessing. Prove the cause first, then solve it.**

---

## When you read this skill: STOP.

Set aside all fix ideas. You will change **nothing** until you know the root cause with 100% certainty.

---

## PHASE 1 — Gather Evidence (observe only, touch nothing)

Answer these 4 questions with real evidence from logs/code:

### 1. What exactly happens?
- Exact error message or stack trace from logs
- HTTP status code (401? 403? 500? Redirect?)
- Which endpoint / function / service is affected
- What the user sees vs. what happens in the backend

### 2. When does it happen?
- Always or only sometimes?
- Only for specific users / roles / inputs?
- Since when — after which commit / change?
- Reproducible in which exact steps?

### 3. What should happen instead?
- Expected behavior in one clear sentence
- Actual behavior in one clear sentence

### 4. What was changed last?
- Last relevant commit
- New ENV variables, new dependencies, new migrations?

**→ STOP. Only proceed to Phase 2 when all 4 questions are answered.**

---

## PHASE 2 — Form a Hypothesis (REQUIRED)

Write ONE concrete, testable hypothesis before touching anything:

```
"The bug occurs because [specific cause],
which I will prove/disprove by [concrete test]."
```

**Good hypothesis:**
```
"The user gets logged out because the JWT is not correctly set 
in the cookie after login, which I'll prove by checking the 
Set-Cookie header in the login response in backend logs."
```

**Bad hypothesis:**
```
"Something is wrong with the auth."
→ Too vague. Try again. Name the specific cause.
```

**Report your hypothesis before continuing.**
Format: `🔬 HYPOTHESIS: [your hypothesis]`

---

## PHASE 3 — Binary Search (narrow down the bug)

Split the problem in half. Test one half.
- Bug is there → split further
- Bug is not there → test the other half

### For API / Backend bugs:
```
Request in → Middleware → Guard → Controller → Service → DB → Response
     ↑              ↑         ↑          ↑          ↑
     Where does the chain break? Test each step individually.
```

### For Auth / Session bugs:
```
Step 1: Login request → is JWT correctly generated?
Step 2: JWT in response → does it reach the client?
Step 3: Follow-up request → is JWT sent in the request?
Step 4: Guard/Middleware → is JWT correctly validated?
Step 5: Secret → is the same secret used for signing and verification?
```

### For Frontend bugs:
```
User action → State update → API call → Process response → UI update
     ↑              ↑            ↑              ↑
     Where does the chain break?
```

**After each test step, report:**
- ✅ [Step X] OK — bug is not here
- ❌ [Step X] BUG FOUND — [what exactly]

---

## PHASE 4 — Fix (only now)

Only when the root cause is proven through Phases 1-3:

1. **Apply minimal fix** — only what fixes the bug, nothing else
2. **Don't refactor while debugging** — one problem, one fix
3. **Test immediately** that the specific bug is gone
4. **Verify** before reporting done

---

## Common Error Patterns

| Symptom | Check First |
|---------|-------------|
| User logged out after login | JWT secret mismatch, Cookie SameSite/Secure settings, CORS config |
| HTTP 401 on authenticated requests | JWT expired, wrong secret, missing Bearer token, validate() not called |
| HTTP 403 | Missing role, Guard logic, Tenant isolation blocking |
| HTTP 500 without stack trace | Unhandled Promise rejection, search console.error in logs |
| "Cannot read property of undefined" | Missing null checks, DB query returning null |
| Route not found (404) | Module not imported in AppModule, wrong controller prefix |
| DB error on startup | Migration not run, column doesn't exist, missing ENV variable |
| Cookie not set | SameSite=None + Secure=true needed for cross-origin |
| Cookie not sent | Cross-origin fetch needs `credentials: 'include'` |

---

## Debug Commands

```bash
# JWT decode manually
echo "$TOKEN" | cut -d. -f2 | base64 -d | jq .

# Test login + auth flow
curl -X POST http://localhost:4000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@test.com","password":"test"}' \
  -c /tmp/cookies.txt -v 2>&1 | grep "Set-Cookie"

curl http://localhost:4000/api/auth/me \
  -b /tmp/cookies.txt -v 2>&1 | grep "HTTP"

# What's using this port?
lsof -i :PORT

# Git bisect — find which commit introduced the bug
git bisect start
git bisect bad              # current commit is broken
git bisect good abc1234     # known good commit
# Test each checkout, then: git bisect good / git bisect bad
git bisect reset
```

For framework-specific debugging commands, see:
- `references/nestjs.md` — NestJS + Next.js
- `references/patterns.md` — Common bug patterns with real examples

---

## Required Reporting Format

```
🔍 DEBUG REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bug: [Exact error message from logs]
Located: [File:Line / Function / Service]
Root cause: [What actually happened — one clear explanation]
Evidence: [How the cause was proven]
Fix: [What was changed exactly — file + what]
Verified: [Yes — how tested, which test is green]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Escalation Protocol

If the bug still exists after **3 complete phase cycles**:

1. **Document everything** — write a full summary of what was tried and why it didn't work
2. **Escalate with context** — don't just say "it's broken", say:
   ```
   🚨 ESCALATION NEEDED
   Bug: [description]
   Tried: [3 hypotheses + what was proven/disproven]
   Current state: [what we know for certain]
   Help needed: [specific question or fresh eyes]
   ```
3. **Options:**
   - Ask a second developer / AI instance with full context
   - Revert to last known working commit and debug the diff
   - Add extensive logging and let it run in staging to gather more data
   - Temporarily disable the feature and fix properly later

**Rule: Never spend more than 3 cycles without escalating or reverting.**

---

## Absolute Rules

- **NEVER** fix without a hypothesis from Phase 2
- **NEVER** change multiple things at once
- **NEVER** "try something to see if it helps" — evidence-based fixes only
- **NEVER** skip a phase because the fix seems obvious
- After 3 fix attempts without resolution → **escalate using the Escalation Protocol above**
- **Scope discipline:** Fix only the reported bug, don't touch other issues
