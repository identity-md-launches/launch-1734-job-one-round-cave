"""Raw-proof replay and adversarial comparisons; synthetic headers are test-only."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import code_frontier_delta as tool

proof = tool.frontier.targets.calls.proof
lens = tool.lens


def read(path):
    return tool.read_json(HERE.parent / path)


def synthetic_runtime(code, height_delta=1):
    """Construct a test-only single-account trie; never saved as chain evidence."""
    bundle = read('code-proof/zto-proof.json')
    node = bundle['observation']['nodes'][0]
    node.update(code='0x' + code.hex(), code_bytes=len(code), code_hash=lens.digest(code))
    node['storage'] = {name: '0x' + '00' * 32 for name in lens.SLOTS}
    bundle['observation']['effective_code_hash'] = node['code_hash']
    account = proof.rlp_encode([b'\x01', b'', proof.EMPTY_TRIE,
                                bytes.fromhex(node['code_hash'][2:])])
    leaf = proof.rlp_encode([b'\x20' + proof.keccak256(bytes.fromhex(node['address'][2:])), account])
    header = proof.rlp_decode(bytes.fromhex(bundle['header_rlp'][2:]))
    header[3] = proof.keccak256(leaf)
    header[8] = proof.integer_bytes(proof.scalar(header[8]) + height_delta)
    encoded = proof.rlp_encode(header)
    bundle['header_rlp'] = '0x' + encoded.hex()
    bundle['observation']['block'] = {'number': hex(proof.scalar(header[8])),
                                       'hash': lens.digest(encoded)}
    bundle['proofs'] = [{'address': node['address'], 'nonce': '0x1', 'balance': '0x0',
                         'storageHash': '0x' + proof.EMPTY_TRIE.hex(),
                         'codeHash': node['code_hash'], 'accountProof': ['0x' + leaf.hex()],
                         'storageProof': [{'key': key, 'value': '0x0', 'proof': []}
                                          for key in lens.SLOTS.values()]}]
    return bundle


class FrontierDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zto_old = read('code-proof/zto-proof.json')
        cls.zto = read('code-routes/zto-proof.json')
        cls.imd = read('code-routes/imd-proof.json')
        cls.target = read('code-target-proofs/imd-target-proof.json')

    def test_real_zto_endpoint_identity(self):
        report = tool.compare(self.zto_old, [], self.zto, [])
        self.assertEqual(report['decision'], 'same-bounded-scan')
        self.assertEqual(report['comparison_mode'], 'historical-endpoint-comparison')
        self.assertEqual(report['block_distance'], 2929)
        self.assertEqual(report['runtime_evidence']['unchanged_count'], 1)
        self.assertFalse(report['continuous_stability_verified'])
        self.assertFalse(report['common_chain_ancestry_verified'])

    def test_real_imd_evidence_expansion_preserves_unknowns(self):
        report = tool.compare(self.imd, [], self.imd, [self.target])
        self.assertEqual(report['comparison_mode'], 'same-block-evidence-comparison')
        self.assertEqual(report['decision'], 'bounded-scan-differences')
        self.assertEqual(report['before']['unresolved_call_site_count'], 11)
        self.assertEqual(report['after']['unresolved_call_site_count'], 34)
        self.assertEqual(len(report['unresolved_sites']['present_in_both_scans']), 11)
        self.assertEqual(len(report['unresolved_sites']['only_after_scan']), 23)
        self.assertEqual(report['runtime_evidence']['only_after_scan'][0]['runtime_bytes'], 24005)
        edge = report['constant_edges']['changed'][0]
        self.assertEqual(edge['before']['status'], 'missing-proof')
        self.assertEqual(edge['after']['status'], 'proved-runtime')
        self.assertIsNone(edge['before']['target_code_hash'])
        self.assertEqual(edge['after']['target_code_hash'],
                         self.target['observation']['nodes'][0]['code_hash'])
        self.assertFalse(report['dependency_completeness_verified'])

    def test_withdrawn_evidence_does_not_claim_resolved_sites(self):
        report = tool.compare(self.imd, [self.target], self.imd, [])
        self.assertEqual(len(report['runtime_evidence']['only_before_scan']), 1)
        self.assertEqual(len(report['unresolved_sites']['only_before_scan']), 23)
        self.assertEqual(report['after']['decision'], 'open-frontier')
        self.assertEqual(report['after']['missing_constant_targets'],
                         [self.target['observation']['target']])

    def test_identical_open_frontier_does_not_become_closed(self):
        report = tool.compare(self.imd, [self.target], self.imd, [self.target])
        self.assertEqual(report['decision'], 'same-bounded-scan')
        self.assertEqual(report['after']['decision'], 'open-frontier')
        self.assertEqual(len(report['unresolved_sites']['present_in_both_scans']), 34)
        self.assertFalse(report['semantic_safety_verified'])

    def test_changed_runtime_does_not_reuse_same_pc_identity(self):
        old = synthetic_runtime(b'\xf1\x00', 1)
        new = synthetic_runtime(b'\xf1\x5b', 2)
        report = tool.compare(old, [], new, [])
        self.assertEqual(len(report['runtime_evidence']['changed']), 1)
        sites = report['unresolved_sites']
        self.assertEqual(sites['only_before_scan'][0]['pc'], 0)
        self.assertEqual(sites['only_after_scan'][0]['pc'], 0)
        self.assertNotEqual(sites['only_before_scan'][0]['caller_code_hash'],
                            sites['only_after_scan'][0]['caller_code_hash'])
        self.assertEqual(sites['present_in_both_scans'], [])

    def test_changed_caller_keeps_constant_edge_identities_separate(self):
        prefix = b'\x73' + bytes.fromhex(lens.IMD[2:]) + b'\x60\x01\xf1'
        report = tool.compare(synthetic_runtime(prefix + b'\x00', 1), [],
                              synthetic_runtime(prefix + b'\x5b', 2), [])
        edges = report['constant_edges']
        self.assertEqual(len(edges['only_before_scan']), 1)
        self.assertEqual(len(edges['only_after_scan']), 1)
        self.assertEqual(edges['changed'], [])
        self.assertEqual(report['missing_constant_targets']['present_in_both_scans'], [lens.IMD])

    def test_different_targets_and_reverse_order_refused(self):
        with self.assertRaisesRegex(ValueError, 'different source'):
            tool.compare(self.zto, [], self.imd, [])
        with self.assertRaisesRegex(ValueError, 'precedes'):
            tool.compare(self.zto, [], self.zto_old, [])

    def test_same_height_fork_refused_after_raw_proofs_verify(self):
        old, fork = synthetic_runtime(b'\xf1\x00'), synthetic_runtime(b'\xf1\x5b')
        self.assertTrue(proof.verify(old)['state_inclusion_verified'])
        self.assertTrue(proof.verify(fork)['state_inclusion_verified'])
        with self.assertRaisesRegex(ValueError, 'equal block heights have different hashes'):
            tool.compare(old, [], fork, [])

    def test_corrupt_source_proof_on_either_side_refused(self):
        for side in (0, 1):
            pair = [copy.deepcopy(self.zto_old), copy.deepcopy(self.zto)]
            pair[side]['proofs'][0]['accountProof'].pop(0)
            with self.assertRaises(ValueError):
                tool.compare(pair[0], [], pair[1], [])

    def test_forged_self_consistent_target_runtime_refused(self):
        forged = copy.deepcopy(self.target)
        node = forged['observation']['nodes'][0]
        node.update(code='0x00', code_bytes=1, code_hash=lens.digest(b'\x00'))
        forged['observation']['effective_code_hash'] = node['code_hash']
        forged['proofs'][0]['codeHash'] = node['code_hash']
        self.assertTrue(lens.verify(forged['observation']))
        with self.assertRaisesRegex(ValueError, 'proven code hash'):
            tool.compare(self.imd, [], self.imd, [forged])

    def test_wrong_block_unrelated_duplicate_and_excess_target_proofs_refused(self):
        with self.assertRaisesRegex(ValueError, 'same block'):
            tool.compare(read('code-proof/imd-proof.json'), [self.target], self.imd, [])
        for bundles, message in (([self.zto], 'unrelated'),
                                  ([self.target, self.target], 'duplicate'),
                                  ([self.target] * 17, 'at most 16')):
            with self.assertRaisesRegex(ValueError, message):
                tool.compare(self.imd, [], self.imd, bundles)

    def test_each_anchor_checked_separately_and_never_authenticated(self):
        old_hash = self.zto_old['observation']['block']['hash']
        new_hash = self.zto['observation']['block']['hash']
        report = tool.compare(self.zto_old, [], self.zto, [], old_hash, new_hash)
        self.assertTrue(report['before']['caller_supplied_anchor_hash_matched'])
        self.assertTrue(report['after']['caller_supplied_anchor_hash_matched'])
        self.assertFalse(report['anchor_authenticity_verified'])
        for anchors in ((new_hash, new_hash), (old_hash, old_hash)):
            with self.assertRaisesRegex(ValueError, 'independent block hash'):
                tool.compare(self.zto_old, [], self.zto, [], *anchors)
        report = tool.compare(self.zto_old, [], self.zto, [], old_hash)
        self.assertFalse(report['after']['caller_supplied_anchor_hash_matched'])

    def test_case_normalized_source_and_additional_roots_without_mutation(self):
        source, target = copy.deepcopy(self.imd), copy.deepcopy(self.target)
        for bundle in (source, target):
            bundle['observation']['target'] = '0x' + bundle['observation']['target'][2:].upper()
        before = copy.deepcopy((source, target))
        report = tool.compare(source, [target], self.imd, [self.target])
        self.assertEqual(report['decision'], 'same-bounded-scan')
        self.assertEqual((source, target), before)

    def test_saved_success_report_is_not_raw_evidence(self):
        report = tool.compare(self.zto, [], self.zto, [])
        with self.assertRaises((KeyError, ValueError)):
            tool.compare(report, [], self.zto, [])

    def test_cli_exit_contract_and_no_partial_json_on_refusal(self):
        command = [sys.executable, '-B', str(HERE / 'code_frontier_delta.py')]
        zto = str(HERE.parent / 'code-routes/zto-proof.json')
        imd = str(HERE.parent / 'code-routes/imd-proof.json')
        target = str(HERE.parent / 'code-target-proofs/imd-target-proof.json')
        for extra, expected in ((['--before-source', zto, '--after-source', zto], 0),
                                (['--before-source', imd, '--after-source', imd,
                                  '--after-target-proof', target], 3),
                                (['--before-source', zto, '--after-source', imd], 1),
                                ([], 2)):
            process = subprocess.run(command + extra, capture_output=True, text=True, timeout=30)
            self.assertEqual(process.returncode, expected, process.stderr)
            if expected in (0, 3):
                self.assertTrue(json.loads(process.stdout)['raw_proofs_reverified'])
            else:
                self.assertEqual(process.stdout, '')

    def test_reader_refuses_outside_workspace_and_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, 'inside workspace'):
            tool.read_json(Path.cwd().parent / 'outside.json')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            json.loads('{"schema":1,"schema":2}',
                       object_pairs_hook=tool.frontier.targets.calls.ancestry.no_duplicates)

    def test_demonstration(self):
        import demo
        self.assertTrue(demo.main()['demonstration_passed'])


if __name__ == '__main__':
    unittest.main()
