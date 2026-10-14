# Allowance Code Bytes

Recompute the byte lengths and SHA-256 hashes of active ERC-20 spenders from saved `eth_getCode` returns, and bind those bytes to the exact permission inventory and historical block. This closes the previous Code Context tool's reliance on unexamined runtime-hash claims. Python 3.10+, standard library only; all dependencies are ordinary source files already in this line.

From the repository root, run the offline real-ZTO demonstration:

```sh
python3 -B line-2/tools/code-bytes/code_bytes.py
```

## What happened when tried

The real ZTO inventory at Ethereum block **26,187,572**, hash `0xfbdf6fb511bd7ee2e74dd1b2bd8982e05e2d4cf8d10e495e6b9789bc50e7997f`, contains 19 measured pairs, three active permissions and two distinct active spenders. Two active permissions have empty balances; they remain active.

A new read-only historical capture through `https://eth.drpc.org` returned:

| Spender | Bytes | Recomputed SHA-256 |
| --- | ---: | --- |
| `0x40aa958dd87fc8305b97f2ba922cddca374bcd7f` | 2,133 | `b7a42c1c65ed0b591fad1c32c22823e41c2e94caa431594851bbab03798d4161` |
| `0x765956a7307222346b08fff681820a5d77e92028` | 8,285 | `a7c56e8700c1e29c247625aaeb2f9daeb25a2a91b3a422a75566032a1c0b6df4` |

Both match the ancestor's PublicNode report. `zto-code-bytes.json` contains actual raw returns, request parameters and before/after block headers, not synthetic examples. `live-result.json` records the derived `bytes_matched` result. PublicNode was attempted first and returned historical-state-unavailable; `live-attempts.json` records both outcomes. This is a new collection of historical code, not a refresh of allowances or a claim about today's state. Different provider labels do not authenticate provider independence.

Sixteen focused tests passed: altered bytes, forged hashes/lengths, missing and extra coverage, empty code, malformed/oversized hex, duplicates, canonical block pins, identity and header mismatches, wrong methods, input immutability, digests, exact real RPC replay, bounded duplicate-rejecting loading and CLI exits.

## Inputs and collection

```sh
python3 -B line-2/tools/code-bytes/code_bytes.py --observation path/to/inventory.json --runtime path/to/runtime.json --bytes path/to/raw-code.json
```

Use raw Allowance Lens/Changes evidence, a Spender Code `active-allowance-spender-code-v1` report, and this tool's `allowance-code-bytes-evidence-v1` capture. All files must resolve inside the current workspace, at most 96 KiB apiece. Duplicate JSON keys are refused. A code return is strictly even-length hexadecimal, up to 32,768 bytes; this is a deliberate bounded-tool limit. Reports can originate from a different documented provider, but chain, token, block number/hash, permission header and raw request pins must match. Every overlapping raw code/report entry must agree on recomputed length and SHA-256. Missing or extra rows prevent a successful match.

Optionally collect the bytes again with public read-only RPC:

```sh
python3 -B line-2/tools/code-bytes/code_bytes.py --capture --endpoint https://eth.drpc.org --save line-2/tools/code-bytes/new-capture.json
```

The default uses ZTO first and PublicNode. Custom `--observation` and `--runtime` must be supplied together. The collector checks chain identity, checks the canonical block at its height, requests code with `requireCanonical: true` and the exact block hash, then rechecks the block. A separate worker enforces a total deadline (default 45 seconds, configurable 1–55). Only `eth_chainId`, `eth_getBlockByNumber` and `eth_getCode` are allowed. Transport uses an explicit User-Agent, disables environment-derived proxies and rejects redirects. Failed capture never writes a saved evidence file; existing files are never overwritten.

Exit **0**: bytes and context match. Exit **3**: incomplete/extraneous coverage, with permissions retained. Exit **1**: malformed, inconsistent or unavailable evidence. Parsed input SHA-256 digests bind all three inputs. The program does not emit policy approval.

```sh
python3 -B -m unittest discover -s line-2/tools/code-bytes -p 'test_*.py' -v
```

## Limits

Matching SHA-256 checks supplied bytes against earlier claims. It does **not** prove Ethereum account/code inclusion or authenticate headers, RPC returns, providers or current state. A consistent fabricated input set can still match. Code presence or absence does not establish behavior, controller, proxy implementation, delegated execution or safety. Unknown spenders, Permit2, signatures and custom authorizations remain outside coverage. Empty balances and empty code never revoke allowances; per-pair exposure bounds overlap by owner. No key, wallet, secret, environment-variable reading, signing, transaction sending, payment, deployment or application posting is used.
