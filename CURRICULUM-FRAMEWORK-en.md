# Curriculum Framework — ESP32 Cybersecurity Awareness Labs
### For instructors planning a unit around these 10 activities

Each lab file already carries its own "Ethical and Legal Framework," "Discussion," and "Checklist" sections. This document sits **above** all of them: it's the single framework an instructor uses to plan, sequence, supervise, and assess the whole set as one coherent unit, instead of ten disconnected demos.

---

## 1. Purpose & Scope

Ten hands-on labs, one ESP32 DevKit V1 each, teaching wireless/Bluetooth security concepts by making an invisible attack or leak *visible*, then turning it into a defense discussion. No lab requires internet access to be granted, no lab collects real credentials, and no lab is a "build a tool to use later" exercise — every artifact is disposable and classroom-bound.

Full lab index: see [README.md](README.md#-the-labs).

---

## 2. Master Ethical & Legal Framework

Every lab's own framework section is a specific instance of these five rules. Apply all five, every time, regardless of which lab is running:

1. **Informed consent, announced out loud, before power-on.** Not a syllabus footnote — say it in the room, every session: what the device will do, whose devices are involved, and what happens to any data collected.
2. **No real targets, ever.** Every AP created is disposable and grants no internet. Every "attack" (Lab 9) is hard-locked to a device the ESP32 itself created. Nothing in this set may be pointed at the school's production network, a classmate's home network, or any network/device the operator doesn't own or have explicit written permission to test.
3. **Test data only.** Any lab with a form (Evil Twin, Realistic Portal) is briefed with "test data only" *before* connecting, not after. Real credentials should never reach the log in the first place.
4. **Passive-observation labs stay anonymous.** Probe/fingerprint data (Labs 1, 3, 4) is shown as a "wall," never attributed to a named student in front of the class.
5. **Every lab ends on defense, not on the trick.** The closing move is always "here's how you'd have caught or prevented this" — never the exploit itself.

> Legal note to repeat verbatim to students: everything here is legal **only** because it runs against equipment the operator owns/controls, with consent, in a supervised setting. The identical technique against someone else's device or network is a computer-misuse crime in most jurisdictions (e.g. the US Computer Fraud and Abuse Act), regardless of intent or whether real harm occurs.

---

## 3. Risk Tiers

Not all ten labs carry the same blast radius. Use this to decide supervision level and whether extra announcements are needed.

| Tier | Meaning | Labs |
|---|---|---|
| **1 — Passive listening** | Reads broadcasts already in the air; never transmits an attack or fake identity | [Ghost of Networks Past (1)](01-ghost-of-networks-past-en.md), [Wi-Fi Ghost (3)](03-wifi-motion-ghost-through-wall-en.md), [Fingerprint Mirror (4)](04-digital-fingerprint-mirror-en.md), [Deauth Canary (2)](02-deauth-canary-wifi-smoke-alarm-en.md) |
| **2 — Active, opt-in only** | Broadcasts a fake AP/identity, but only affects a device that chooses to connect | [Evil Twin (0)](evil-twin-awareness-guideline-en.md), [Karma (6)](06-karma-wifi-pineapple-explained-en.md), [Realistic Portal (7)](07-realistic-captive-portal-reveal-en.md), [Invisible Ink (5)](05-invisible-ink-ssid-covert-channel-en.md) |
| **3 — Active, reaches bystanders** | Broadcast is visible to *every* nearby device, not just consenting ones | [Bluetooth Poltergeist (8)](08-bluetooth-poltergeist-ble-spam-en.md) |
| **4 — Real attack traffic** | Transmits genuine unauthenticated attack frames; hard-locked to a self-created target | [Deauth Storm (9)](09-deauth-storm-self-target-en.md) |

**Rule of thumb:** Tier 1 needs standard classroom consent. Tier 2 needs per-device consent from whoever connects. Tier 3 needs room-wide announcement to everyone present, run briefly. Tier 4 needs the instructor to visually confirm the code is unmodified (still self-targeting) before every run.

---

## 4. Standards / Domain Mapping

| # | Lab | Domain(s) | Core Concept | Risk Tier |
|---|---|---|---|---|
| 0 | Evil Twin | Social Engineering, Network Security | Rogue AP & captive portal phishing | 2 |
| 1 | Ghost of Networks Past | Privacy, Wireless Security | Probe-request metadata leak | 1 |
| 2 | Deauth Canary | Blue Team / Detection | Building the defender, not the attacker | 1 |
| 3 | Wi-Fi Ghost | Privacy, RF/Side-channel | RSSI-based presence sensing | 1 |
| 4 | Fingerprint Mirror | Privacy, Network Security | Device fingerprinting & MAC tracking | 1 |
| 5 | Invisible Ink | Network Security (advanced) | Covert channels & air-gap myths | 2 |
| 6 | Karma | Social Engineering, Network Security | Auto-connect / Wi-Fi Pineapple mechanics | 2 |
| 7 | Realistic Portal | Social Engineering | Why "professional-looking" ≠ safe | 2 |
| 8 | Bluetooth Poltergeist | Wireless Security (BLE) | Unauthenticated advertising / identity spoofing | 3 |
| 9 | Deauth Storm | Network Security, Blue Team / Detection | Real attack frames, paired with Lab 2's detector | 4 |

Use this table to pull a subset if your course only has room for one unit (e.g. "Social Engineering" → Labs 0, 6, 7; "Blue Team" → Labs 2 + 9 as a pair).

---

## 5. Suggested Sequence (5-session unit)

| Session | Labs | Why this order |
|---|---|---|
| 1 — Hook | Fingerprint Mirror (4) → Ghost of Networks Past (1) | Zero setup friction, biggest "it already knows this?" reaction, establishes passive-leak intuition |
| 2 — Social engineering | Evil Twin (0) → Realistic Portal (7) | Builds from a plain fake login to a polished one; the reveal in (7) lands harder once (0) set the baseline |
| 3 — Wireless mechanics | Karma (6) → Wi-Fi Ghost (3) | (6) is the natural sequel to session 1's leak; (3) shifts the register toward "radio reveals more than you think" |
| 4 — Attack & defense pair | Deauth Canary (2) *then* Deauth Storm (9), same class period | Build the detector first so students understand *why* it works before they watch it fire against a real burst |
| 5 — Wrap-up / advanced | Bluetooth Poltergeist (8) → Invisible Ink (5) → synthesis discussion | (8) needs a room-wide heads-up, so save it for a session where that's already the norm; (5) is the most abstract, good closer before the final discussion |

Adjust freely — the only hard constraint is **Canary (2) before Storm (9)**, so the detection concept exists before students watch the attack it catches.

---

## 6. Master Assessment Rubric

Use across every lab instead of writing ten separate rubrics. Score each row 1–4 (Emerging / Developing / Proficient / Advanced).

| Criterion | Emerging (1) | Developing (2) | Proficient (3) | Advanced (4) |
|---|---|---|---|---|
| **Technical understanding** | Can describe what happened | Can describe *how* it happened at a high level | Can explain the specific protocol weakness exploited | Can explain the weakness *and* propose a concrete fix |
| **Ethical/legal reasoning** | Recites "don't do this to others" | Explains *why* consent/scope changes legality | Distinguishes this lab's risk tier from another's | Argues a defensible position on a gray-area case (e.g. Lab 8's bystander reach) |
| **Defense application** | Names the mitigation from the lab's table | Explains *why* the mitigation works | Applies the mitigation to a novel scenario | Identifies a gap the mitigation doesn't cover |
| **Communication** | Completes the checklist | Contributes to discussion | Asks a question that advances the group's understanding | Connects this lab's concept to a prior lab or real-world case |

---

## 7. Pre-Lab Consent & Supervision Checklist (run before *every* session)

- [ ] Stated out loud what the device will do and what data (if any) it touches
- [ ] Confirmed every participating device belongs to a consenting student
- [ ] For Tier 3 labs: announced to **everyone present**, not just participants
- [ ] For Tier 4 labs: visually confirmed the code is unmodified — still self-targeting, no hardcoded external BSSID
- [ ] Confirmed no AP created in this session grants real internet access
- [ ] Briefed "test data only" *before* any form is shown, not after
- [ ] Planned time for the defense/awareness discussion — not skipped for time
- [ ] Cleared or reviewed-then-deleted any logs collected (SPIFFS `/log.txt`, Serial history) before the next class uses the same board

---

## 8. Cross-Cutting Learning Objectives

By the end of the full sequence, a student should be able to:

1. Explain why several common wireless/Bluetooth protocols trust unauthenticated broadcasts (probe requests, SSIDs, BLE advertising, management frames)
2. Distinguish a passive information leak from an active impersonation attack, and both from a real disruptive attack
3. State, for each lab, the specific real-world mitigation and why it works
4. Articulate the legal boundary between "the same technique, run here vs. run against a stranger's network" — and why that boundary exists independent of technical difficulty
5. Describe what a defender-side tool (the Canary) looks for, and why detection matters even when prevention isn't perfect
