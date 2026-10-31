# RIFT CTF 2026 — Writeups

Writeups for **RIFT CTF 2026 — KageX AI × GeekHaven, IIIT Allahabad**, an AI/LLM-security-focused CTF. Challenges are LLM-backed "desk" chatbots and agents (billing, permits, catalogues, deploy pipelines, etc.) where the goal is to break prompt/trust boundaries, abuse tool access, or exploit agent logic to recover a hidden flag.

## Team

| Member | Solves |
|---|---|
| **Hrishikesh** | Atrium, Shelfmark, Paternoster, Lantern, Meridian, Gantry, Keystone |
| **codeitishant** | Foundry, Cornice, Plinth, Oriel, Corbel |
| **parthsujit07** | Ledger, Quoin, Spandrel |

## Challenges

| Challenge | Category | Solved by | Flag | Writeup |
|---|---|---|---|---|
| [Atrium](Atrium/writeup.md) | AI / Prompt Injection (indirect, via user-supplied context) | Hrishikesh | `FLAG{2c94ae3d135eb87d08dbda1c1f8ef309}` | [writeup.md](Atrium/writeup.md) |
| [Ledger](<Ledger/LEDGER Billing Assistant — Prompt Injection Writeup.md>) | AI / Prompt Injection (output-filter bypass) | parthsujit07 | `FLAG{91d43bfc956beee985c897aeb885dd08}` | [writeup.md](<Ledger/LEDGER Billing Assistant — Prompt Injection Writeup.md>) |
| [Shelfmark](Shelfmark/writeup.md) | AI / LLM Security — Prompt Injection & System Prompt Leakage | Hrishikesh | `FLAG{a74440384927b397d1f3f73417af3b1b}` | [writeup.md](Shelfmark/writeup.md) |
| [Foundry](Foundry/writeup.md) | AI / LLM Tool Abuse (Web) | codeitishant | `FLAG{703a98001233c978784109a00e465344}` | [writeup.md](Foundry/writeup.md) |
| [Paternoster](Paternoster/writeup.md) | AI / LLM Agent Logic Abuse | Hrishikesh | `FLAG{f1c8c11d76d779bae6fcc7d8edf1831d}` | [writeup.md](Paternoster/writeup.md) |
| [Lantern](Lantern/writup.md) | AI / LLM Access-Control Abuse | Hrishikesh | `FLAG{520f251ccb83dad0622ab657efbed26c}` | [writup.md](Lantern/writup.md) |
| [Meridian](Meridian/writup.md) | AI / LLM Workflow Manipulation | Hrishikesh | `FLAG{2a3ed2aac5870986221a8305a41e0444}` | [writup.md](Meridian/writup.md) |
| [Cornice](Cornice/writeup.md) | AI Security / Web — Indirect Prompt Injection | codeitishant | `FLAG{a3c43579e1e96a8613695514decef182}` | [writeup.md](Cornice/writeup.md) |
| [Gantry](Gantry/writeup.md) | AI Agent / Prompt Injection, Logic-Gate Abuse | Hrishikesh | `FLAG{70726c2346757991264aa039f0b4bf10}` | [writeup.md](Gantry/writeup.md) |
| [Plinth](Plinth/writeup.md) | AI Security / Web — LLM Pipeline, Indirect Prompt Injection, Trust-Boundary Bypass | codeitishant | `FLAG{c73066b8888c528a059aa9df6b50516a}` | [writeup.md](Plinth/writeup.md) |
| [Keystone](Keystone/writeup.md) | AI / LLM Security | Hrishikesh | `FLAG{237d94ae12a16e584c37a42274f2770a}` | [writeup.md](Keystone/writeup.md) |
| [Oriel](Oriel/writeup.md) | AI Security / Web — LLM Briefing Assembly, Output Screening | codeitishant | `FLAG{7327473b2008230f20756d2404f01fa3}` | [writeup.md](Oriel/writeup.md) |
| [Quoin](Quoin/quoin-writeup.md) | AI Security / Agent Logic Exploitation | parthsujit07 | `FLAG{f9dcd75835cce32e6e8f873de74ee804}` | [quoin-writeup.md](Quoin/quoin-writeup.md) |
| [Spandrel](<Sprandrel/Spandrel WRITEUP.md>) | Web / AI Agent — Lexicographic Oracle Abuse | parthsujit07 | `FLAG{48fa2a53256f57fa866fa8ba590cb701}` | [Spandrel WRITEUP.md](<Sprandrel/Spandrel WRITEUP.md>) |
| [Corbel](Corbel/writeup.md) | AI / Web — LLM Agent, Permit State Machine | codeitishant | `FLAG{f4bfc6b0053ea4a18e9e98a74601bca3}` | [writeup.md](Corbel/writeup.md) |

**Total solved: 15 / 15 attempted**, score contributions above sum to **5977 pts**.

## Recurring vulnerability patterns

Nearly every challenge in this event reduces to one of a handful of classic LLM-application weaknesses:

- **Indirect prompt injection** — untrusted data (visitor names, patch descriptions, scanned documents, reviews) is concatenated into the model's context and treated as trusted instructions. *(Atrium, Cornice, Plinth, Gantry)*
- **Output-filter / policy-screen bypass** — a second model or regex filter screens responses, but can be tricked into passing secrets through encoding, formatting, or indirection. *(Ledger, Oriel)*
- **System prompt / hidden-context leakage** — getting the assistant to reveal instructions or data it was told to keep private. *(Shelfmark)*
- **Agent tool/logic abuse** — exploiting the state machine or tool-call sequencing of an agentic workflow rather than the model's language understanding directly. *(Meridian, Keystone, Paternoster, Corbel, Quoin)*
- **Side-channel / oracle abuse** — using an application endpoint's behavior (e.g. which bucket a value sorts into) as a comparison oracle to exfiltrate a hidden value byte-by-byte. *(Spandrel)*
- **Access-control / authorization-purpose confusion** — getting an agent to authorize an action under a purpose it wasn't actually permitted to allow. *(Lantern)*

## Repository layout

Each challenge has its own folder named after the challenge, containing a `writeup.md` and, where relevant, supporting `scripts/` or `evidence/` used during the solve.

```
<Challenge>/
  writeup.md       # full solve walkthrough
  scripts/         # exploit/PoC scripts (if any)
  evidence/        # request/response captures, screenshots (if any)
```
