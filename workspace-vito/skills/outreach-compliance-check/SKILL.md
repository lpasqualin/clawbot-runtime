---
name: outreach-compliance-check
description: Run a compliance and ethics checklist before any cold outreach email, DM, or sequence is sent. Use before every cold email, LinkedIn DM, Instagram DM, email sequence, or newsletter to non-opt-in lists. Never skip this check. Never auto-send on YELLOW or RED.
metadata: {"openclaw":{"emoji":"🛡️"}}
---

# Outreach Compliance Check

A governance skill. Run this before every outreach message Vito sends.
This is not optional. This is policy enforcement.

## When To Run

Run before:
- Cold emails
- LinkedIn outreach
- Instagram DMs
- Email sequences
- Newsletters to non-opt-in lists

## Checklist

### CAN-SPAM (US)
- [ ] Real sender name and company are included
- [ ] Physical mailing address is included
- [ ] Clear opt-out mechanism exists (unsubscribe link or "reply STOP")
- [ ] Subject line is not deceptive or misleading

### GDPR-Style Sanity
- [ ] Person is being contacted for a legitimate business reason
- [ ] Message only uses business data (name, company, role)
- [ ] No sensitive personal data included in message body

### FTC
- [ ] No false or unverifiable claims
- [ ] No fake testimonials or fabricated social proof
- [ ] No fake urgency or fake scarcity
- [ ] Not impersonating another person or brand

## Decision System

### 🟢 GREEN — OK to send
All of the following are true:
- Sender is clearly identified
- Subject line is honest
- Opt-out is included
- Business address is included
- All claims are realistic and verifiable
- Recipient is relevant to the offer

### 🟡 YELLOW — Ask Leo before sending
Any of the following are true:
- Lead was scraped and source is unclear
- Message contains performance claims ("we guarantee X results")
- Uses urgency language ("only 3 spots left", "today only")
- 1-to-1 manual email with no unsubscribe (not bulk, but flagged)
- First name personalization pulled from scraped data

### 🔴 RED — Do NOT send. Rewrite first.
Any of the following are true:
- Subject line uses fake reply/forward format (RE:, FWD: when not a reply)
- Fake scarcity or fake testimonials
- Sender identity is hidden or unclear
- Message is going to a purchased bulk list
- Unsubscribe is hidden or absent in bulk send
- Contains misleading claims ("official partner", "certified by Google" when not true)

## Output Format

Always output the result in this exact format:
```
Compliance Check Result:

CAN-SPAM:  PASS / FAIL / WARNING – [reason]
GDPR:      PASS / FAIL / WARNING – [reason]
FTC:       PASS / FAIL / WARNING – [reason]

Overall:   GREEN / YELLOW / RED

Action:    [one of the following]
           GREEN  → OK to send.
           YELLOW → Ask Leo for approval before sending.
           RED    → Do not send. Rewrite the message first. [explain what needs fixing]
```

## Hard Rules

- Never auto-send on YELLOW. Always ask Leo.
- Never auto-send on RED. Always rewrite first.
- If unsure whether a claim is verifiable, treat it as YELLOW.
- If unsure whether the lead source is clean, treat it as YELLOW.
- This check must run even if Vito is confident the message is fine.
