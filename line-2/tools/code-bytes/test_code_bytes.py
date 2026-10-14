import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import code_bytes as tool


class ByteTests(unittest.TestCase):
    def setUp(self):
        self.observation, self.runtime = tool.context.demo_inputs()
        self.evidence = tool.gate.load(tool.HERE / 'zto-code-bytes.json')

    def check(self):
        return tool.check(self.observation, self.runtime, self.evidence)

    def test_real_zto_bytes(self):
        r = self.check()
        self.assertTrue(r['bytes_matched'])
        self.assertEqual([x['bytes'] for x in r['recomputed_spenders']], [2133, 8285])
        self.assertEqual((r['measured_pair_count'], r['active_pair_count'],
                          r['empty_balance_active_pair_count']), (19, 3, 2))
        self.assertFalse(r['complete_wallet_audit'])

    def test_changed_byte_refused(self):
        row = self.evidence['reads'][0]
        row['result'] = '0x' + ('00' if row['result'][2:4] != '00' else '01') + row['result'][4:]
        with self.assertRaisesRegex(ValueError, 'length/hash'):
            self.check()

    def test_forged_hash_and_length_refused(self):
        for key, value in (('runtime_code_bytes', 1), ('runtime_code_sha256', 'a' * 64)):
            with self.subTest(key=key):
                runtime = copy.deepcopy(self.runtime)
                runtime['spenders'][0][key] = value
                with self.assertRaisesRegex(ValueError, 'length/hash'):
                    tool.check(self.observation, runtime, self.evidence)

    def test_missing_bytes_preserves_active_permission(self):
        row = self.evidence['reads'].pop()
        r = self.check()
        self.assertFalse(r['bytes_matched'])
        self.assertEqual(r['missing_byte_spenders'], [row['params'][0]])
        self.assertEqual(r['active_pair_count'], 3)

    def test_missing_report_preserves_unknown(self):
        self.runtime['spenders'].pop()
        r = self.check()
        self.assertFalse(r['bytes_matched'])
        self.assertEqual(len(r['missing_active_spenders']), 1)

    def test_extra_bytes_withhold_match(self):
        known = {r['params'][0] for r in self.evidence['reads']}
        spender = next(s for _, s in tool.gate.changes.flatten(self.observation)['pairs'] if s not in known)
        row = copy.deepcopy(self.evidence['reads'][0])
        row['params'][0] = spender
        self.evidence['reads'].append(row)
        self.assertEqual(self.check()['extra_byte_spenders'], [spender])
        self.assertFalse(self.check()['bytes_matched'])

    def test_empty_code_does_not_clear_permission(self):
        self.evidence['reads'][0]['result'] = '0x'
        self.runtime['spenders'][0].update(runtime_code_bytes=0,
            runtime_code_sha256=hashlib.sha256(b'').hexdigest(), classification='no_runtime_code_at_block')
        r = self.check()
        self.assertTrue(r['bytes_matched'])
        self.assertEqual(r['active_pair_count'], 3)
        self.assertTrue(any(x['status'] == 'active_permission_without_runtime' for x in r['pairs']))

    def test_malformed_hex_refused(self):
        for value in ('0x0', '0x00 00', '0xgg', '00', None, '0x' + '00' * 32769):
            with self.subTest(value=str(value)[:20]), self.assertRaises(ValueError):
                tool.bytecode(value)
        self.assertEqual(tool.bytecode('0xABcd'), bytes.fromhex('abcd'))

    def test_duplicate_read_refused(self):
        self.evidence['reads'].append(copy.deepcopy(self.evidence['reads'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.check()

    def test_exact_canonical_pin(self):
        for pin in ('latest', {'blockHash': self.evidence['block_hash'], 'requireCanonical': 1},
                    {'blockHash': '0x' + 'ab' * 32, 'requireCanonical': True}):
            e = copy.deepcopy(self.evidence)
            e['reads'][0]['params'][1] = pin
            with self.assertRaises(ValueError):
                tool.check(self.observation, self.runtime, e)

    def test_context_identity(self):
        for field, value in (('chain_id', True), ('block_number', True), ('token', 'IMD'),
                             ('token_address', tool.lens.TOKENS['IMD']), ('source', 'https://example.com')):
            e = copy.deepcopy(self.evidence)
            e[field] = value
            with self.assertRaises(ValueError):
                tool.check(self.observation, self.runtime, e)

    def test_headers_are_bound(self):
        for field, value in (('hash', '0x' + 'ab' * 32), ('number', '0x1'), ('timestamp', '0x1')):
            for both in (True, False):
                e = copy.deepcopy(self.evidence)
                e['headers'][0][field] = value
                if both:
                    e['headers'][1][field] = value
                with self.assertRaises(ValueError):
                    tool.check(self.observation, self.runtime, e)

    def test_method_and_unknown_fields(self):
        self.evidence['reads'][0]['method'] = 'eth_call'
        with self.assertRaisesRegex(ValueError, 'eth_getCode'):
            self.check()
        self.evidence['reads'][0]['method'] = 'eth_getCode'
        self.evidence['invented'] = True
        with self.assertRaisesRegex(ValueError, 'exactly'):
            self.check()

    def test_immutable_inputs_and_digest(self):
        old = copy.deepcopy((self.observation, self.runtime, self.evidence))
        result = self.check()
        self.assertEqual(old, (self.observation, self.runtime, self.evidence))
        self.assertEqual(result['input_sha256']['bytes'], tool.context.digest(self.evidence))

    def test_capture_replays_exact_real_reads_and_rechecks_block(self):
        expected = [('eth_chainId', [], '0x1'),
                    ('eth_getBlockByNumber', [hex(self.evidence['block_number']), False], self.evidence['headers'][0])]
        expected += [(r['method'], r['params'], r['result']) for r in self.evidence['reads']]
        expected += [('eth_getBlockByNumber', [hex(self.evidence['block_number']), False], self.evidence['headers'][1])]
        calls = []
        def rpc(_self, method, params):
            wanted, args, result = expected[len(calls)]
            self.assertEqual((method, params), (wanted, args))
            calls.append(method)
            return copy.deepcopy(result)
        with patch.object(tool.CodeRPC, 'call', rpc):
            captured = tool.capture(self.observation, self.runtime, self.evidence['source'])
        self.assertEqual(captured, self.evidence)
        self.assertEqual(len(calls), 5)

    def test_loader_and_cli_exits(self):
        scratch = Path.cwd() / 'test/scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, '-B', str(tool.HERE / 'code_bytes.py')]
        p = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            path = Path(directory) / 'input.json'
            path.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                tool.gate.load(path)
            path.write_bytes(b' ' * (tool.gate.LIMIT + 1))
            with self.assertRaisesRegex(ValueError, '96 KiB'):
                tool.gate.load(path)
            self.evidence['reads'].pop()
            path.write_text(json.dumps(self.evidence))
            p = subprocess.run(command + ['--bytes', str(path)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 3, p.stderr)
            self.evidence['reads'][0]['result'] = '0x0'
            path.write_text(json.dumps(self.evidence))
            p = subprocess.run(command + ['--bytes', str(path)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 1, p.stderr)
        with self.assertRaises(ValueError):
            tool.gate.load(Path.cwd().parent / 'not-in-workspace.json')


if __name__ == '__main__':
    unittest.main()
