import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import zto_witness_policy as tool


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.a, self.ca = copy.deepcopy(tool.replay.demo_inputs())
        self.b, self.cb = copy.deepcopy((self.a, self.ca))
        # A synthetic second label exercises policy only, not provider independence.
        self.b['base']['source'] = self.cb['source'] = 'https://second.example/rpc'
        self.policy = {'schema': 'zto-witness-policy-v1',
                       'expected_block_hash': self.a['base']['block']['hash'],
                       'reference_block': int(self.a['base']['block']['number'], 16),
                       'max_age_blocks': 0, 'input_token': 'ZTO',
                       'maximum_input_raw': str(10**18), 'maximum_slippage_bps': 100,
                       'sources': {self.a['base']['source']: 'first', self.b['base']['source']: 'second'}}

    def run_review(self, token='ZTO', amount='1', bps=100):
        return tool.review(self.a, self.b, self.ca, self.cb, self.policy, token, amount, bps)

    def withheld(self, reason, **kwargs):
        result = self.run_review(**kwargs)
        self.assertFalse(result['bound_released'])
        self.assertIsNone(result['bound'])
        self.assertIn(reason, result['reasons'])

    def test_demo_real_evidence_no_network(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            result = tool.demo()
        self.assertEqual(result['raw_quoter_matches'], [True, True])
        self.assertEqual(result['reasons'], ['same_source_label', 'same_receiver_provider_group'])
        self.assertIsNone(result['bound'])

    def test_simulated_distinct_approved_groups(self):
        result = self.run_review()
        self.assertTrue(result['bound_released'])
        self.assertEqual(result['bound']['planning_minimum_raw'], '15139234039518')
        self.assertEqual(result['receiver_policy_sha256'], tool.replay.digest(self.policy))
        self.assertEqual(len(result['evidence_sha256']), 4)

    def test_same_group_different_urls(self):
        self.policy['sources'][self.b['base']['source']] = 'first'
        self.withheld('same_receiver_provider_group')

    def test_unknown_source_cannot_choose_own_group(self):
        del self.policy['sources'][self.b['base']['source']]
        self.withheld('source_not_approved_by_receiver')

    def test_exact_source_label(self):
        self.b['base']['source'] = self.cb['source'] = 'https://second.example/rpc/'
        self.withheld('source_not_approved_by_receiver')

    def test_raw_input_ceiling_and_boundary(self):
        self.assertTrue(self.run_review()['bound_released'])
        self.policy['maximum_input_raw'] = str(10**18-1)
        self.withheld('input_exceeds_receiver_ceiling')

    def test_slippage_ceiling(self):
        self.withheld('slippage_exceeds_receiver_ceiling', bps=101)
        self.assertTrue(self.run_review(bps=99)['bound_released'])

    def test_direction_policy(self):
        self.policy['input_token'] = 'IMD'
        self.withheld('input_token_outside_receiver_policy')

    def test_age_limit(self):
        self.policy['reference_block'] += 1
        self.withheld('outside_caller_age_limit')
        self.policy['max_age_blocks'] = 1
        self.assertTrue(self.run_review()['bound_released'])

    def test_wrong_anchor(self):
        self.policy['expected_block_hash'] = self.a['base']['initialize']['blockHash']
        self.withheld('caller_block_anchor_mismatch')

    def test_raw_evidence_still_recomputed(self):
        self.ca['results'][0]['request']['data'] += '00'
        with self.assertRaisesRegex(ValueError, 'quoter request'):
            self.run_review()

    def test_strict_policy_types_and_keys(self):
        for key, value in [('maximum_input_raw', '01'), ('maximum_input_raw', str(1<<127)),
                           ('maximum_input_raw', True), ('maximum_slippage_bps', True),
                           ('reference_block', True), ('max_age_blocks', -1),
                           ('input_token', 'ETH'), ('sources', {}), ('schema', 'wrong')]:
            with self.subTest(key=key, value=value):
                policy = copy.deepcopy(self.policy); policy[key] = value
                with self.assertRaises(ValueError):
                    tool.validate_policy(policy)
        self.policy['extra'] = 'ignored?'
        with self.assertRaisesRegex(ValueError, 'policy fields'):
            self.run_review()

    def test_group_canonicalization_refuses_ambiguity(self):
        for group in ('FIRST', ' first', 'first ', '', True, 'x'*65):
            with self.subTest(group=group):
                self.policy['sources'][self.a['base']['source']] = group
                with self.assertRaisesRegex(ValueError, 'provider group'):
                    self.run_review()

    def test_cli_demo_and_conflicting_inputs(self):
        script = str(Path(tool.__file__))
        run = subprocess.run([sys.executable, '-B', script, '--demo'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse(json.loads(run.stdout)['bound_released'])
        run = subprocess.run([sys.executable, '-B', script, '--demo', '--amount', '1'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)


if __name__ == '__main__':
    unittest.main()
