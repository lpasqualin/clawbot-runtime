# Real Bug Patterns — Lessons Learned

Documented bugs with root cause analysis and fixes.

---

## JWT Secret Mismatch
**Symptom:** User logged out immediately after login, `/auth/me` returns 401

**The trap:** `JwtModule.register()` and `JwtStrategy` had **different fallback secrets**:
- Login signed with: `'secret-A'`
- Strategy verified with: `'secret-B'`

**How to prove:** Add temporary `console.log` in `validate()` in JwtStrategy → if it's NEVER called → signature verification fails → secrets don't match

**Fix:** Align fallback secrets in both places. Better: fail-fast if `JWT_SECRET` ENV is missing.

---

## Cross-Origin Cookie Problem
**Symptom:** Login successful, but all API calls return 401

**The trap:** `fetch()` from the browser does NOT send cookies on cross-origin requests (localhost:3000 → localhost:4000), even with `credentials: 'include'` and Next.js rewrites configured.

**Why Next.js rewrites don't help:** Rewrites only work for **server-side** requests, not client-side `fetch()`.

**Fix:** Ensure all API calls run through the **same origin** (Next.js as proxy) OR return JWT in response body and send via `Authorization` header.

---

## NestJS Global Prefix Duplication
**Symptom:** 404 on all API routes after adding global prefix

**The trap:** Controller path `api/something` + global prefix `api` → results in `/api/api/something`

**Fix:** NEVER prefix controller paths with `api/` when global prefix is already `api`. Use only the resource name.

---

## React Rules of Hooks Violation
**Symptom:** React crashes on render, `Invalid hook call` error

**The trap:** `useState` or `useEffect` called after an early return in a component.

**Fix:** All hooks MUST be called at the top of the component, before any early returns.
