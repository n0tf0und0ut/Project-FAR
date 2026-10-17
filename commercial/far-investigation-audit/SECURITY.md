# FAR Investigation Lab — Prototype Threat Model

Status: Research. No production certification, no public deployment authorization.

## Threats and bounded mitigations

| Threat | Mechanism currently implemented | Remaining limitation |
|---|---|---|
| SSRF, DNS rebinding, redirects | HTTPS/443, credential-free public FQDN, reject reserved/private DNS, pin resolved IP during TLS handshake, revalidate redirect | Public hosts can themselves serve malicious/harmful content; optional yt-dlp has different network stack |
| Prompt injection in source material | Source content passed as explicitly untrusted data; model has no tool-call authority; schema, literal quotes and source-ID references validated | System prompts do not prevent all manipulation; extraction can still be biased |
| Citation laundering | Exact quote/source identity and hash required, source leads not automatically evidence, self-corroboration prohibited | Exact quote is not proof of support, source origin, reliability or independence |
| Unsupported inference | Exhaustive finite entailment with countermodels, separate bitmask algorithm and inconsistency block | Formula translation itself is unverified; finite Boolean logic does not establish causation/generalization |
| Temporal leakage | Hindsight gate requires captured/published eligibility; undated source stays unknown; remote capture clock cannot be backdated | Provider-model pretraining and external historical archive authenticity not verifiable |
| Input and compute exhaustion | Bounded sources, claims, formula depth, atom count, JSON rows, source sizes, download size/redirects, model context/output, subprocess timeouts | No distributed quotas; local process and optional tools still have resource costs |
| Browser XSS, untrusted URLs | CSP, nosniff, local-only default, `textContent` for report output; no arbitrary HTML rendering of source | No account authentication; do not deploy on public host |
| Unauthorized remote disclosure | Network and model are separately opt-in; local audio upload requires consent and server enablement | Operator is responsible for upstream processor data handling, copyright, privacy and provider billing |
| Report tampering | SHA-256 per file, full replay, design-diverse logic verification, Ed25519 review signature check | Without independent key custody, attacker can replace entire unsigned package self-consistently |

## Explicit nonclaims

No certification, model-internal-reasoning access, source authenticity proof,
secure multi-user cloud service, validation of expert judgment, statistical
causal identification or complete protection from prompt injection.

Never log API secrets, export raw production media without authorization, or
interpret a cryptographic hash as an attested third-party source identity.
