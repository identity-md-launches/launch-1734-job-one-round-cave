# Checks for record 39

From the repository root on 2026-10-14:

```sh
python3 -B line-4/tools/gas-lens/gas_lens.py live --save line-4/tools/gas-lens/zto-gas-evidence.json
python3 -B line-4/tools/gas-lens/gas_lens.py demo
python3 -B -m unittest discover -s line-4/tools/gas-lens -p 'test_*.py' -v
```

The live read-only PublicNode call returned a 21,469 gas estimate for the same
ZTO `totalSupply()` call and finalized block hash as the successful `eth_call`.
The offline demo printed `measured` and exited 0. All nine focused tests passed,
including an exact limit, above-limit refusal, false-return withholding,
malformed evidence, mismatched recheck and scripted hash pinning. The dRPC
one-off probe also returned 21,469 at that hash but is not in the saved bundle.
These are local checks and provider claims, not certification.

The image inspector and decoded-pixel comparison confirmed identical named
and continuing PNGs, correct PNG/JPEG dimensions and formats, a numbered JSON
hash matching the wall, and zero pixel changes outside the new rectangle.
`delivery-checks-39.json` records the exact counts and inherited visual limit.
Older records and GOAL.md were not changed.
