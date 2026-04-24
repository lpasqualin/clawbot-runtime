# NestJS / Next.js Specific Debugging

**Kein blindes Fixen. Kein Raten. Erst beweisen, dann lösen.**

## Trigger-Wörter (Skill sofort laden)

Dieser Skill wird **sofort aktiviert** wenn der User eines dieser Wörter schreibt:
- `debug`
- `debugg`
- `debugge`
- `debugging`
- `tief debuggen`
- `tief analysieren`

Auch aktivieren bei: "warum funktioniert X nicht", "immer noch kaputt", "schau tiefer", "such mal tiefer".

## Wann diesen Skill verwenden

IMMER wenn:
- Der User "debug", "debugg" oder ähnliches schreibt
- Ein Bug beim ersten Fix-Versuch nicht behoben wurde
- Blind Dinge ausprobiert werden ohne die Ursache zu kennen
- Der User "funktioniert nicht" meldet ohne klare Fehlermeldung
- Auth/Session-Probleme auftreten
- HTTP 401/403/500 ohne klaren Stack Trace
- Ein Bug nach mehreren Fix-Versuchen immer noch existiert

**NIEMALS direkt fixen ohne diesen Skill durchlaufen zu haben.**

---

## Wenn du diesen Skill liest: STOPP.

Leg alle Fix-Ideen beiseite. Du wirst NICHTS ändern bevor du die Ursache zu 100% kennst.

---

## PHASE 1 — Daten sammeln (nur beobachten, nichts anfassen)

Beantworte diese 4 Fragen mit echten Beweisen aus Logs/Code:

### 1. Was genau passiert?
- Exakte Fehlermeldung oder Stack Trace aus den Logs
- HTTP Status Code (401? 403? 500? Redirect?)
- Welcher Endpoint / welche Funktion / welcher Service ist betroffen
- Was sieht der User vs. was passiert im Backend

### 2. Wann passiert es?
- Immer oder nur manchmal?
- Nur bei bestimmten Usern / Rollen / Inputs?
- Seit wann — nach welchem Commit / welcher Änderung?
- Reproduzierbar in welchen Schritten genau?

### 3. Was sollte stattdessen passieren?
- Erwartetes Verhalten klar in einem Satz benennen
- Tatsächliches Verhalten klar in einem Satz benennen

### 4. Was wurde zuletzt geändert?
- Letzter relevanter Commit
- Neue ENV-Variablen, neue Abhängigkeiten, neue Migrationen?

**→ STOPP. Erst wenn alle 4 Fragen beantwortet sind: weiter zu Phase 2.**

---

## PHASE 2 — Hypothese aufstellen (PFLICHT)

Formuliere EINE konkrete, testbare Hypothese bevor du irgendetwas anfasst:

```
"Der Fehler tritt auf weil [konkrete Ursache],
was ich beweise/widerlege indem ich [konkreter Test]."
```

**Gute Hypothese:**
```
"Der User wird rausgeworfen weil das JWT nach dem Login nicht 
korrekt im Cookie gesetzt wird, was ich beweise indem ich 
den Set-Cookie Header in der Login-Response in den Backend 
Logs überprüfe."
```

**Schlechte Hypothese:**
```
"Irgendwas stimmt mit der Auth nicht."
→ Zu vage. Nochmal. Konkrete Ursache benennen.
```

**Melde die Hypothese bevor du weitermachst.**
Format: `🔬 HYPOTHESE: [deine Hypothese]`

---

## PHASE 3 — Binary Search (Fehler eingrenzen)

Teile das Problem in zwei Hälften. Teste eine Hälfte.
- Liegt der Fehler dort → weiter aufteilen
- Liegt er nicht dort → andere Hälfte testen

### Für Auth/Session-Bugs (häufigster Fall):
```
Schritt 1: Login-Request → wird JWT korrekt generiert?
 → Logs: POST /auth/login → 200 oder Fehler?

Schritt 2: JWT im Response → landet er korrekt beim Client?
 → Set-Cookie Header vorhanden? LocalStorage befüllt?

Schritt 3: Folge-Request → wird JWT mitgeschickt?
 → Authorization: Bearer [token] im Request-Header? Cookie present?

Schritt 4: Guard/Middleware → wird JWT korrekt validiert?
 → JwtAuthGuard wirft 401? Welche Fehlermeldung?

Schritt 5: JWT_SECRET → ist er korrekt gesetzt?
 → Gleicher Secret beim Generieren (JwtModule) und Validieren (JwtStrategy)?
```

### Für allgemeine API-Bugs:
```
Request rein → Middleware → Guard → Controller → Service → DB → Response
     ↑              ↑          ↑         ↑           ↑
     Wo bricht die Kette? Jeden Schritt einzeln testen.
```

### Für Frontend-Bugs:
```
User-Action → State-Update → API-Call → Response verarbeiten → UI-Update
     ↑              ↑           ↑              ↑
     Wo bricht die Kette?
```

**Melde nach jeder Testphase:**
- ✅ [Schritt X] OK — Fehler liegt nicht hier
- ❌ [Schritt X] FEHLER GEFUNDEN — [was genau]

---

## PHASE 4 — Fix (erst jetzt)

Nur wenn die Ursache durch Phase 1-3 bewiesen ist:

1. **Minimalen Fix implementieren** — nur das was den Fehler behebt, nichts anderes
2. **Nicht gleichzeitig refactoren** — ein Problem, ein Fix
3. **Direkt testen** ob der spezifische Fehler weg ist
4. **Verification** ausführen bevor "fertig" gemeldet wird

---

## Häufige Fehlerquellen (NestJS/Next.js-Stack)

| Symptom | Zuerst prüfen |
|---|---|
| User wird nach Login rausgeworfen | JWT_SECRET Mismatch zwischen JwtModule und JwtStrategy, Cookie SameSite/Secure Settings, CORS-Config |
| HTTP 401 bei authentifizierten Requests | JWT expired, falscher Secret, Bearer Token fehlt im Header, `validate()` wird nicht aufgerufen |
| HTTP 403 | Rolle fehlt, Guard-Logik prüfen, Tenant-Isolation blockiert |
| HTTP 500 ohne Stack Trace | Unbehandelte Promise-Rejection, console.error in Logs suchen |
| "Cannot read property of undefined" | Null-checks fehlen, DB-Query gibt null zurück |
| Route nicht gefunden (404) | Module nicht in AppModule importiert, falscher Controller-Prefix |
| DB-Fehler beim Start | Migration nicht ausgeführt, Spalte existiert nicht, ENV-Variable fehlt |
| Cookie wird nicht gesetzt | SameSite=None + Secure=true nötig bei Cross-Origin; SameSite=Lax für same-site |
| Cookie wird nicht mitgeschickt | Cross-Origin Fetch braucht `credentials: 'include'`, Next.js Rewrites funktionieren nur SSR-seitig |
| JWT Strategy extrahiert Token aber 401 | `secretOrKey` in JwtStrategy stimmt NICHT mit secret in JwtModule überein (Fallback-Wert-Problem!) |

---

## Debugging-Tools (NestJS/Next.js)

```bash
# Backend Live-Logs mit tee
npm run start:dev 2>&1 | tee /tmp/backend-debug.log

# JWT manuell dekodieren
echo "$TOKEN" | cut -d. -f2 | base64 -d | jq .

# Login + /me curl-Test
curl -X POST http://localhost:4000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"...","password":"..."}' \
  -c /tmp/cookies.txt -v 2>&1 | grep "Set-Cookie"

curl http://localhost:4000/api/auth/me \
  -b /tmp/cookies.txt -v 2>&1 | grep "HTTP"

# Prüfe ob JWT-Strategy validate() aufgerufen wird
# → Temporäres console.log in validate() hinzufügen
# → Wenn log NICHT erscheint: Signatur-Verifikation schlägt fehl → Secret-Mismatch!
```

---

## Reporting-Format (PFLICHT nach jedem Debugging)

```
🔍 DEBUG REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fehler: [Exakte Fehlermeldung aus Logs]
Lokalisiert: [Datei:Zeile / Funktion / Service]
Ursache: [Was wirklich passiert ist — eine klare Erklärung]
Beweis: [Wie die Ursache bewiesen wurde]
Fix: [Was genau geändert wurde — Datei + was]
Verifiziert: [Ja — wie getestet, welcher Test grün]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Absolute Regeln

- **NIEMALS** fixen ohne Hypothese aus Phase 2
- **NIEMALS** mehrere Dinge gleichzeitig ändern
- **NIEMALS** "probieren ob es hilft" — nur beweisbasierte Fixes
- **NIEMALS** Phase überspringen weil der Fix "offensichtlich" wirkt
- Wenn nach 3 Fix-Versuchen der Bug noch existiert → zurück zu Phase 1, neue Hypothese
- **Scope-Disziplin:** Nur den gemeldeten Bug fixen, keine anderen Baustellen anfassen

---

## Lessons Learned (aus echten Bugs)

### JWT Secret Mismatch (2026-03-19)
**Symptom:** User wird nach Login sofort rausgeworfen, `/auth/me` gibt 401

**Falle:** `JwtModule.register()` und `JwtStrategy` hatten **unterschiedliche Fallback-Secrets**:
- Login signierte mit: `'caresys-super-secret-jwt-key-2026'`
- Strategy verifizierte mit: `'fallback-secret-for-dev'`

**Beweis-Methode:** `validate()` in JwtStrategy temporär loggen → wurde NIE aufgerufen → Signatur-Verifikation schlägt fehl → Secrets stimmen nicht überein

**Fix:** Fallback-Secret in `jwt.strategy.ts` angleichen:
```typescript
secretOrKey: process.env.JWT_SECRET || 'caresys-super-secret-jwt-key-2026',
```

### Cross-Origin Cookie Problem (2026-03-19)
**Symptom:** Login erfolgreich, aber alle API-Calls geben 401

**Falle:** `fetch()` vom Browser sendet Cookies **NICHT** bei Cross-Origin-Requests (localhost:3000 → localhost:4000), auch wenn `credentials: 'include'` gesetzt ist und Next.js Rewrites konfiguriert sind.

**Warum Next.js Rewrites nicht helfen:** Rewrites funktionieren nur für **SSR-seitige** Requests, nicht für client-side `fetch()`.

**Fix:** Sicherstellen dass alle API-Calls über die **gleiche Origin** laufen (Next.js als Proxy) ODER JWT auch im Response-Body zurückgeben und im `Authorization` Header senden.
