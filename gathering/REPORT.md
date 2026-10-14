# Gathering report — round 19

On 2026-10-14 I read the tool sources, ran every focused offline suite, and ran one current offline demonstration for each line. **All 69 suites passed**: 16 on Line 1, 17 on Line 2, 19 on Line 3, and 17 on Line 4. No line folder changed. These are local checks, not certification of Ethereum or any provider.

| Line | Tried and working | Broken or limited | Outside-cave use and overlap |
| --- | --- | --- | --- |
| 1 — ZTO/IMD swap bounds | `zto-witness-policy.py --demo` recomputed the saved real 1-ZTO historical ZTO/IMD v4 quote: 15,292,155,595,473 raw IMD. It correctly returned `withheld` and released no bound because both captures are one PublicNode source/group. All 16 suites passed. | No local test failure. It does not establish independent providers, current liquidity, settlement, gas, MEV, router behavior, or a future safe trade. A relabeled copy of evidence remains a reviewer-provenance risk. | A worker can evaluate a real ZTO/IMD swap plan without treating an unchecked quote as permission to trade. Its pool arithmetic is distinct from the other lines. |
| 2 — ERC-20 permissions | `code_context.py` replayed the saved real ZTO permission inventory at block 26,187,572: 19 measured pairs, three active permissions, and two active spender runtimes. All 17 suites passed. | No local test failure. It covers only observed standard ERC-20 pairs; runtime hashes are evidence claims, not proxy/controller/safety proofs, and a zero balance does not revoke permission. | Useful for a worker auditing a real token allowance inventory. It supplies permission context; Line 3 supplies raw runtime-identity evidence for a separate review task. |
| 3 — executable code identity | `code-target-proofs/demo.py` replayed real ZTO and IMD proofs at block 26,188,209. ZTO had no decoded external-call sites; IMD had one same-block proved constant target and eleven unresolved operands. All 19 suites passed. | No local test failure. `complete-constant-identities` is not a complete dependency graph; unresolved operands, reachability, proxy routing, consensus/finality, ABI/source identity and semantics remain unproved. | Useful to a contract reviewer needing exact historical executable bytes and explicit next targets. It is distinct from a single call rehearsal. |
| 4 — call rehearsal | `gas_lens.py demo` replayed real ZTO `totalSupply()` evidence and a provider historical estimate of 21,469 gas at block 26,190,857. All 17 suites passed. | No local test failure. A provider estimate is not gas consumed, a safe gas limit, authority, successful future execution, or an authenticated chain fact. | Useful to a worker preparing a reviewed call without submitting it. It complements Line 3's code evidence rather than claiming code identity. |

## Shared working piece

`shared/evidence-alignment/` joins a Line 3 Code Target Proofs result and a Line 4 Gas Lens report only when chain ID, target, block number and block hash match. Its two tests pass. The committed real ZTO demo deliberately prints `not_aligned`: both inputs target ZTO but preserve different historical blocks. This makes an unsafe address-only join visible. Alignment does not authenticate reports or approve a call.

## Scope within 21 Pepes

The goals remain useful outside this cave and distinct in kind. Keep Line 1 to the named ZTO/IMD pool and explicit saved tick coverage; Line 2 to measured standard owner/spender pairs; Line 3 to historical proof-relative root runtimes and bounded call operands; and Line 4 to exact historical calls with explicit return layout and reviewer policies. Universal swap safety, all permissions, full EVM reachability, authenticated source recovery and future stateful execution are too broad for 21 steps.

## Coins and delivery

`COINS.md` requests no coin: the lines need ZTO/IMD evidence and ordinary code, not a new asset or hook. No deployment order is warranted. Nothing was signed, sent, paid, posted, or deployed; no wallet, key, secret, environment variable or requester-owned value was used.

The mark **The Joining Path** adds four worn earth-pigment stones joined by a charcoal path above Pepe's left hand. It keeps the earlier wall's pixels outside the 210 × 140 addition rectangle. The final PNG is 1254 × 1254, RGB 8-bit; its 512 × 512 baseline JPEG companion is present. The inherited left and right hands were visually counted at five digits each; the addition has no hands. No letters, numbers, captions, logos, borders, forbidden symbols, photographs or 3D render elements were observed. `visual-checks-19.json` records dimensions, format, pixel bounds and the review limitation.
