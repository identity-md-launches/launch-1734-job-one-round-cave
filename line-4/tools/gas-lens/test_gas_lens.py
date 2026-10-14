"""Focused offline checks; mutation cases are synthetic, not chain observations."""
import copy
import json
from pathlib import Path
import unittest

import gas_lens as gas


class GasLensTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = gas.load(Path(__file__).with_name('zto-gas-evidence.json'))

    def test_real_zto_replay(self):
        result = gas.evaluate(self.saved)
        self.assertEqual(result['verdict'], 'measured')
        self.assertEqual(result['estimate_gas'], '21469')
        self.assertEqual(result['call']['to'], gas.core.TOKENS['ZTO'])
        self.assertEqual(result['block']['hash'], self.saved['observation']['block']['hash'])

    def test_reviewer_bound_is_inclusive(self):
        self.assertEqual(gas.evaluate(self.saved, '21469')['verdict'], 'within_limit')
        self.assertEqual(gas.evaluate(self.saved, '21468')['verdict'], 'above_limit')

    def test_invalid_policy_refused(self):
        for value in ('0', '021469', '-1', '2.1', '9' * 100):
            with self.subTest(value=value[:24]), self.assertRaises(ValueError):
                gas.evaluate(self.saved, value)

    def test_rechecked_header_must_match(self):
        bundle = copy.deepcopy(self.saved)
        bundle['recheck']['hash'] = '0x' + '12' * 32
        with self.assertRaisesRegex(ValueError, 'rechecked header'):
            gas.evaluate(bundle)

    def test_reported_estimate_failure_is_inconclusive(self):
        bundle = copy.deepcopy(self.saved)
        bundle['estimate'] = {'error': {'code': -32000, 'message': 'unavailable'}}
        result = gas.evaluate(bundle, '30000')
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertIsNone(result['estimate_gas'])

    def test_false_return_never_passes_bound(self):
        bundle = copy.deepcopy(self.saved)
        bundle['observation']['returns'] = 'bool'
        bundle['observation']['outcome']['result'] = '0x' + '00' * 32
        result = gas.evaluate(bundle, '30000')
        self.assertEqual(result['call_status'], 'returned_false')
        self.assertEqual(result['verdict'], 'inconclusive')

    def test_malformed_bundle_and_estimate_refused(self):
        bundle = copy.deepcopy(self.saved)
        bundle['extra'] = True
        with self.assertRaises(ValueError):
            gas.evaluate(bundle)
        bundle = copy.deepcopy(self.saved)
        bundle['estimate'] = {'result': '0x'}
        with self.assertRaises(ValueError):
            gas.evaluate(bundle)
        bundle = copy.deepcopy(self.saved)
        bundle['estimate']['error'] = {'code': 3, 'message': 'bad'}
        with self.assertRaises(ValueError):
            gas.evaluate(bundle)

    def test_capture_uses_exact_hash_pin_and_rechecks(self):
        saved = self.saved
        block = saved['observation']['block']
        calls = []

        class ScriptedRPC:
            endpoint = saved['observation']['source']
            answers = ['0x1', block, '0x60', saved['observation']['outcome']['result'],
                       block, saved['estimate']['result'], block]

            def call(self, method, params):
                calls.append((method, params))
                return self.answers[len(calls) - 1]

        bundle = gas.capture(ScriptedRPC(), saved['observation']['call'], 'uint256')
        self.assertEqual(bundle['estimate']['result'], saved['estimate']['result'])
        self.assertEqual([name for name, _ in calls],
                         ['eth_chainId', 'eth_getBlockByNumber', 'eth_getCode',
                          'eth_call', 'eth_getBlockByNumber', 'eth_estimateGas',
                          'eth_getBlockByNumber'])
        self.assertEqual(calls[5][1][0], saved['observation']['call'])
        self.assertEqual(calls[5][1][1],
                         {'blockHash': block['hash'], 'requireCanonical': True})

    def test_offline_cli_demo_and_limit_exit(self):
        from contextlib import redirect_stdout
        from io import StringIO
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(gas.main(['demo']), 0)
        self.assertEqual(json.loads(out.getvalue())['verdict'], 'measured')
        with redirect_stdout(StringIO()):
            self.assertEqual(gas.main(['demo', '--max-gas', '21468']), 1)


if __name__ == '__main__':
    unittest.main()
