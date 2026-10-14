# Evidence Alignment

Join Line 3's historical Code Target Proofs report to Line 4's Gas Lens report
only when chain, contract address, block number and block hash are identical.
This prevents a gas estimate from being associated with code seen at another block.

Run the real, offline ZTO replay from the repository root:

```sh
python3 -B shared/evidence-alignment/evidence_alignment.py
```

It prints `not_aligned`: both inputs concern real ZTO, but their saved blocks are
different. That is the intended safe result. An `aligned` result is only context
alignment, not transaction approval or a safety claim.

```sh
python3 -B -m unittest discover -s shared/evidence-alignment -p 'test_*.py' -v
```

The tool is Python standard library only, reads committed workspace-local JSON,
and makes no network, wallet, signing, transaction, payment or posting action.
