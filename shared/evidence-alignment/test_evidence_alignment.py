import unittest
from evidence_alignment import align

def code(block="0x1", target="0xd782bdea4ef02a0bd391eb9089470c8080f0a68e"):
    return {"schema": "code-target-proofs-result-v1", "chain_id": 1, "source_target": target,
            "code_block": {"number": block, "hash": "0x" + "1" * 64}, "decision": "complete"}

def gas(block="0x1", target="0xd782bdea4ef02a0bd391eb9089470c8080f0a68e"):
    return {"schema": "gas-lens-v1", "chain_id": 1, "block": {"number": block, "hash": "0x" + "1" * 64},
            "call": {"to": target}, "verdict": "measured"}

class AlignmentTests(unittest.TestCase):
    def test_exact_context_aligns(self):
        self.assertEqual(align(code(), gas())["status"], "aligned")
    def test_changed_block_or_target_does_not_align(self):
        self.assertEqual(align(code("0x2"), gas())["status"], "not_aligned")
        self.assertEqual(align(code(), gas(target="0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7"))["status"], "not_aligned")

if __name__ == "__main__":
    unittest.main()
