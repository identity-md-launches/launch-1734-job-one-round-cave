# ZTO Witness Policy

Apply a receiver's independently supplied policy to saved ZTO/IMD Uniswap v4 liquidity and Quoter evidence. Exact approved source labels must belong to two different receiver-assigned provider groups. The candidate must also satisfy the receiver's input direction, raw input ceiling, slippage ceiling, pinned block hash and age limit. Every quote is recomputed through ZTO Witness Replay; a sender's precomputed report is never accepted as evidence.

Python 3.10+ and standard library only. Keep the committed sibling `zto-witness-replay`, `zto-witness`, `zto-path` and `zto-band` folders. From the repository root, one command shows it working without network:

```sh
python3 -B line-1/tools/zto-witness-policy/zto_witness_policy.py --demo
```

The demonstration replays real archived 1-ZTO pool and Quoter evidence at Ethereum block **26,184,260**, yielding **15,292,155,595,473 raw IMD** locally. Both saved inputs come from one PublicNode capture. The result is correctly `withheld`, with `same_source_label` and `same_receiver_provider_group`, and **no bound**. Demo exit 0 means the demonstration ran, not permission to trade. `demo-report.json` records the run. This is historical evidence; no fresh measurement is claimed.

For supplied evidence and your own policy:

```sh
python3 -B line-1/tools/zto-witness-policy/zto_witness_policy.py --snapshot-a PATH_A --snapshot-b PATH_B --quoter-a CHECK_A --quoter-b CHECK_B --policy YOUR_POLICY --input ZTO --amount 1 --slippage-bps 100
```

The policy is a strict JSON object with exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema` | `zto-witness-policy-v1` |
| `expected_block_hash` | Receiver's lowercase bytes32 block anchor |
| `reference_block` | Receiver's uint64 reference height |
| `max_age_blocks` | Receiver's uint64 maximum age |
| `input_token` | `ZTO` or `IMD` |
| `maximum_input_raw` | Positive canonical decimal string, below 2^127, in input-token minor units |
| `maximum_slippage_bps` | Integer 0–9999; bool is refused |
| `sources` | 1–16 exact endpoint labels mapped to reviewer-selected lowercase provider identifiers |

A group identifier has 1–64 lowercase ASCII letters, digits, underscores or hyphens, starting with a letter or digit. URLs differing only by a trailing slash are distinct labels; no normalization silently approves a new source. Assign routes sharing an upstream the **same** group. Never copy a sender's groups merely to make their evidence pass. The tool does not discover providers or establish their independence. A single approved source is a valid policy but cannot release a bound.

Real mode exit **0** means accepted, **2** means withheld, and **1** means malformed input or file error. Syntax errors from argparse conventionally exit 2. JSON reports go to stdout and errors to stderr. A policy refusal never emits a nested usable bound. Reports include canonical policy/evidence SHA-256 digests, source/group labels, raw input and refusal reasons. Those hashes identify parsed input content, not authenticated provenance.

Each JSON input must be within the current workspace and at most 100 KB. The inherited strict reader refuses duplicate keys, JSON floats and nonfinite values. Reports write no files; redirect stdout to an allowed workspace path if desired. No sockets are opened by this tool.

## What happened when tried

All **14 focused offline tests passed**: real single-source replay, simulated approved distinct groups, shared-group refusal, unapproved and subtly changed labels, exact raw ceiling, tolerance ceiling, direction, age, block anchor, altered calldata, strict policy types, canonical group identifiers and CLI behavior. Positive two-group tests relabel copied historical state and are explicitly **synthetic policy tests**, not a second real provider observation. The 59 Replay/Witness/Path/Band dependency tests also passed.

Saved RPC data, block anchors and group assignments remain unauthenticated. Copied evidence relabeled as two approved groups can pass. A reviewer must establish source provenance separately. Arithmetic is inherited and limited to saved tick coverage; age is relative to the receiver's supplied height. The historical floor-rounded planning minimum is unenforced. Future liquidity, token settlement, router behavior, gas and MEV are not modeled. No wallet, key, secret, environment variable, signing, sending, payment, post or deployment is used. The real ZTO/IMD pool is sufficient; no new coin is required.
