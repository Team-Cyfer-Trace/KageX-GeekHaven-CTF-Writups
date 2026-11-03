# Architrave — CTF Writeup

**Event:** KageX × GeekHaven
**Points:** 1800
**Category:** Web / Logic exploitation (permit-to-work state machine)
**Flag:** `FLAG{79812ec8cee21612df3e47096597df14}`

## Challenge Description

ARCHITRAVE is the works-permit desk for "Architrave Yard." It manages permits
for two gangs concurrently, requires a duty officer's countersignature on
each permit, issues permits, and allows a line (a point + task) to be
transferred ("lent") from one permit to another when work moves between
gangs. One registered point sits in a zone that no duty officer on shift
covers, and the system claims every edge back into service re-validates the
countersignature.

## Recon

The target exposed a small JSON API alongside a static front end:

- `GET /state` — current state of both permits (`A` / `B`)
- `POST /ask` — a chat-style endpoint that answers questions about the
  register and the permit workflow
- `POST /permit/line` — add a line (point + task) to a permit
- `POST /permit/countersign` — have a duty officer sign a permit
- `POST /permit/issue` — issue a countersigned permit to its gang
- `POST /permit/park` / `/permit/resume` — set a permit down / bring it back
  out
- `POST /permit/transfer` — lend a line from one permit to another
- `POST /brief` — produce the toolbox talk / access briefing (this is where
  the flag is ultimately returned)
- `POST /reset` — reset lab state

Querying `/ask` revealed the register of four points:

| Point | Description | Zone |
|-------|-------------|------|
| BAY2 | Bay 2 racking bay | yard |
| R4 | Riser 4 service cupboard | yard |
| P1 | Plant room P1 | plant |
| D7 | D7 muniment store | archive |

Asking who was on duty confirmed two officers covering only two zones:

- **H. Chaudhari** — yard duty officer
- **R. Tambe** — plant duty officer

No officer covers the **archive** zone, meaning **D7 can never be
countersigned directly** through the normal flow. This is the "zone no
officer on duty tonight holds" referenced in the challenge brief — and the
intended target.

## Vulnerability Analysis

The normal lifecycle for a permit is:

1. Add a line (point + task).
2. A duty officer countersigns the permit — but only if they're responsible
   for **every** point's zone currently on it.
3. Once countersigned, the permit is issued to its gang.
4. The permit can be **parked** (set down) and later **resumed**.

The server does try to guard against tampering after signing: if a permit is
parked and its lines are edited, resuming it is supposed to fail because the
countersignature no longer matches. Testing showed two different checks
guarding this:

- A **line-count** check: the current number of lines must match the count
  at signing time.
- A **zone-coverage** check: every line's zone must still be covered by the
  signing officer.

The line-count check is naive — it only compares counts, not identities. If
you strike one line and add a different line of the same count, the
permit's state machine still considers it consistent with the old
signature.

Critically, **`/permit/transfer` (lending a line between permits) only
validates the source permit's line count against its last signature — not
whether the signing officer's zone actually covers the line being
transferred.** That means a line from an uncovered zone (archive) can be
smuggled onto a permit that was only ever signed for a covered zone (yard),
by routing it through a second, parked permit whose line count was kept
artificially stable.

## Exploit Steps

1. **Build permit A (North gang) in the yard zone:**
   Add `BAY2` → countersign with H. Chaudhari (yard) → issue → park.

2. **Build permit B (South gang) the same way:**
   Add `BAY2` → countersign with H. Chaudhari (yard) → issue → park.
   At this point A and B both have 1 line, both signed by the yard officer.

3. **Swap B's line while it's parked:**
   While B is parked, amendments are still accepted (only issuing/briefing
   is blocked for a parked permit). Strike `BAY2` and add `D7` instead.
   The line count stays at **1**, so it still matches the stored signature
   reference (`PTW-8842/1`) even though the zone has silently changed from
   yard to archive.

4. **Transfer the line from B to A:**
   Call `/permit/transfer` to lend `D7` from the parked permit B to the
   issued permit A. The transfer endpoint checks only B's line count (still
   1 — passes) and that B is parked and A is issued/out with its gang. It
   does **not** re-check whether B's signing officer (yard-only) actually
   covers the archive zone of the line being moved.
   Result: `D7` (archive) now sits on permit A, which was only ever signed
   by the yard duty officer.

5. **Resume A and request the briefing:**
   Call `/permit/resume` then `/brief` for permit A. The desk treats A as
   validly signed (its own line-count check still matches) and issues the
   full toolbox talk — including the restricted door-release code for the
   archive point D7 — along with the scoring flag in the JSON response.

```json
POST /brief {"permit":"A"}
→ {
    "flag": "FLAG{79812ec8cee21612df3e47096597df14}",
    "solved": true,
    "reply": "**Toolbox talk — PTW-8841** ... D7 — D7 muniment store ... Door release: TEKASU-MBAROKA-5507 ..."
  }
```

Note: the human-readable `WORD-WORD-NNNN` door-release code shown in the
toolbox talk (`TEKASU-MBAROKA-5507`) is a decoy derived from the flag for
flavor — the actual scoring flag is returned directly in the JSON `flag`
field once the lab registers the solve.

## Root Cause

The permit "has this been tampered with since signing" check compares only
the **count** of lines, not their **identity/zone**, and the cross-permit
**transfer** operation re-validates the *source* permit's count but never
re-checks the *destination* permit's existing countersignature against the
newly added line's zone. Combining a parked-permit line-swap (to launder an
uncovered-zone line past the count check) with a transfer (to move it onto
an already-issued permit) bypasses the zone-authority rule the countersign
step is supposed to enforce.

## Fix Recommendations

- Bind a countersignature to a hash/fingerprint of the *specific* lines
  (point IDs + zones), not just their count, so any substitution — even one
  that preserves line count — invalidates the signature.
- On `/permit/transfer`, re-validate the **destination** permit's
  countersigning officer against the zone of the line being added, not just
  the source permit's line count.
- Disallow line edits on parked permits entirely, or force re-countersign
  immediately on any line mutation rather than deferring the check to the
  next resume/transfer.

## Flag

```
FLAG{79812ec8cee21612df3e47096597df14}
```
