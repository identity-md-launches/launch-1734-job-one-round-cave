# Code Frontier Delta

Compare two proof-backed, bounded Ethereum dependency scans before relying on a contract's executable code. The tool reconstructs the raw account, storage, header and runtime proofs on both sides, then shows changed runtime identities, evidence added or removed from the scan, constant-call edges, missing target proofs and unresolved call sites. A saved success report cannot replace the raw proofs.

Run this one command from the repository root, offline, with Python 3.9+ and only the standard library:

```sh
python3 -B line-3/tools/code-frontier-delta/demo.py
```

**What happened when tried:** `demonstration_passed` was `true`; 17 focused tests passed. The demonstration uses saved real ZTO evidence first, then saved real IMD evidence. Its complete results are in `demo-result.json`.

| Comparison | Observed result |
| --- | --- |
| ZTO, block 26,185,280 to block 26,188,209 | Same proved runtime identity and empty structural call scan across endpoints 2,929 blocks apart. This does not prove continuous stability or common-chain ancestry. |
| IMD, block 26,188,209 before and after supplying its saved constant-target proof | One additional runtime becomes visible to the scan, and one missing target proof is filled. The eleven existing unresolved sites remain; the added target runtime contributes twenty-three more, for thirty-four unresolved sites. |

The IMD comparison shows why fewer missing proofs do not imply a closed dependency frontier. The target was already on chain at the same block: its appearance in this report records added evidence, never a new deployment. Reversing this same-block comparison shows withdrawn evidence, never destroyed code or resolved call sites.

For your own raw bundles, use this form (the following saved IMD example intentionally exits **3** because the scans differ):

```sh
python3 -B line-3/tools/code-frontier-delta/code_frontier_delta.py --before-source line-3/tools/code-routes/imd-proof.json --after-source line-3/tools/code-routes/imd-proof.json --after-target-proof line-3/tools/code-target-proofs/imd-target-proof.json
```

Repeat `--before-target-proof` and `--after-target-proof` independently, up to sixteen proofs per side. Each target proof must match its source's exact block number and hash and be reachable through the inherited scan's locally constant target operands. Candidate proofs cannot be unrelated or duplicate roots. Both sources must identify the same Ethereum mainnet address. The after block must be at the same or a later height; equal heights with different hashes are refused. Address casing is normalized without modifying input bundles. All inputs must be workspace-local JSON, at most 100,000 bytes each; duplicate JSON keys and paths resolving outside the workspace are refused.

`--before-anchor-hash` and `--after-anchor-hash` independently compare every raw proof on each side to a caller-selected execution block hash. The result records which equality checks were supplied. Copying a bundled hash does not authenticate it; neither header authenticity nor consensus is established. The default replay makes no network requests. The program prints JSON and writes nothing.

The CLI exits **0** for the same bounded scan, **3** for bounded-scan differences, **1** for refused evidence/context (no partial JSON on stdout), and **2** for argument errors. Exit 0 can still describe an open frontier: inspect each side's `decision`, `missing_constant_targets` and `unresolved_call_site_count`. No exit grants transaction approval. The demonstration exits 0 when its expected real results, including the open IMD case, match.

Runtime rows are compared by address. `runtime_evidence.changed` means both endpoints supply that address with different proved runtime identity or scan details; `only_before_scan` and `only_after_scan` describe visibility in the supplied scans. Missing evidence is never assumed to be an empty account. Constant edges are identified by caller address, caller runtime hash and target address. Their before/after rows include the target runtime hash when available, so a same-address target code change is visible. Unresolved sites are identified by caller address, caller runtime hash, program counter and opcode. A site at the same PC in changed runtime bytes gets separate identities; its disappearance is never called resolution. Every unresolved site from either scan is retained.

This extends Code Dependency Frontier and complements Code Delta: the latter compares candidate proxy-path positions and runtime instruction windows; this piece compares the recursively supplied bounded dependency evidence. The committed sibling modules required for offline use are `code-dependency-frontier`, `code-targets`, `code-calls`, `code-surface`, `code-opcodes`, `code-ancestry`, `code-proof`, and `code-lens` (including Keccak). The demonstration also reads committed proof bundles in `code-proof`, `code-routes` and `code-target-proofs`. No install, configuration change, package dependency, submodule or new coin is needed.

The inherited verifier supports nonempty legacy EVM runtime code and bounded supported proxy candidates. Empty/absent-account proofs and `0xef` execution formats are outside this tool's accepted scope. Structural scanning includes metadata and potentially unreachable instructions. Locally constant operands are conditional on successful local linear execution. Unresolved operands, custom dispatch, beacon implementation call results and actual proxy routing remain unproved. Matching endpoint scans do not establish complete dependencies, current code, continuity, source equivalence, semantic safety or authority to transact. No key, wallet, secret, environment variable, signature, transaction, payment, post or deployment is used.

Run focused checks:

```sh
python3 -B -m unittest discover -s line-3/tools/code-frontier-delta -p 'test_*.py' -v
```

Tests replay the real proofs, expand and withdraw IMD target evidence, preserve unknown sites in identical open scans, reject wrong blocks/targets/anchors and corrupt proofs, reject same-height forks and reversed chronology, verify case normalization without input mutation, and check CLI exits and empty stdout on refusal. Test-only reconstructed trie/header fixtures show that changed runtime bytes at the same PC cannot inherit an old site's identity. These synthetic fixtures are never saved as real chain observations.

The mark's meaning: **Pepe compares proved trails and keeps newly revealed branches visible.**
