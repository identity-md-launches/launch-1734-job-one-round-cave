#!/usr/bin/env python3
"""Recompute active-spender runtime hashes from saved exact-block RPC bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'code-context'))
import code_context as context

gate = context.gate
lens = gate.lens
require = lens.require
SCHEMA = 'allowance-code-bytes-evidence-v1'
MAX_CODE_BYTES = 32768


def bytecode(value):
    require(isinstance(value, str) and len(value) <= 2 + 2 * MAX_CODE_BYTES
            and re.fullmatch(r'0x(?:[0-9a-fA-F]{2})*', value) is not None,
            'runtime must be even-length 0x hex, at most 32768 bytes')
    return bytes.fromhex(value[2:])


def check(observation, runtime, evidence):
    association = context.check(observation, runtime)
    gate.exact_keys(evidence, ('schema', 'source', 'chain_id', 'token', 'token_address',
                              'block_number', 'block_hash', 'headers', 'reads'), 'evidence')
    require(evidence['schema'] == SCHEMA, 'wrong byte-evidence schema')
    require(type(evidence['chain_id']) is int and type(evidence['block_number']) is int,
            'chain and block number must be integers')
    require(evidence['source'] in lens.PUBLIC_ENDPOINTS, 'undocumented byte-evidence source')
    for key in ('chain_id', 'token', 'token_address', 'block_number', 'block_hash'):
        require(evidence[key] == runtime[key], 'byte evidence and runtime differ on ' + key)
    headers = evidence['headers']
    require(isinstance(headers, list) and len(headers) == 2, 'two block headers required')
    for h in headers:
        gate.exact_keys(h, ('number', 'hash', 'timestamp'), 'header')
        lens.header(h)
        require(lens.quantity(h['number']) == evidence['block_number']
                and h['hash'] == evidence['block_hash'], 'byte evidence header differs from block')
    require(headers[0] == headers[1], 'canonical block changed during capture')
    measured = gate.changes.flatten(observation)
    # Preserve the actual permission block timestamp as well as its hash and height.
    observations = observation.get('observations', [observation])
    require(headers[0] == observations[0]['block'], 'byte header and permission header differ')
    reads = evidence['reads']
    require(isinstance(reads, list) and len(reads) <= 64, 'at most 64 code reads allowed')
    by_spender = {}
    for row in reads:
        gate.exact_keys(row, ('method', 'params', 'result'), 'code read')
        require(row['method'] == 'eth_getCode', 'only eth_getCode evidence is supported')
        params = row['params']
        require(isinstance(params, list) and len(params) == 2, 'code read needs address and block pin')
        spender = lens.address(params[0])
        require(params[0] == spender, 'spender must be lowercase')
        gate.exact_keys(params[1], ('blockHash', 'requireCanonical'), 'block pin')
        require(params[1]['blockHash'] == evidence['block_hash']
                and params[1]['requireCanonical'] is True, 'code read must use exact canonical hash')
        require(spender not in by_spender, 'duplicate raw code spender')
        raw = bytecode(row['result'])
        by_spender[spender] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    reports = context.code.validate(runtime)['spenders']
    for spender in set(by_spender) & set(reports):
        require(by_spender[spender] == reports[spender], 'runtime bytes disagree with reported length/hash: ' + spender)
    active = {s for (_, s), row in measured['pairs'].items() if int(row['allowance_raw']) > 0}
    missing = sorted(active - set(by_spender))
    extra = sorted(set(by_spender) - active)
    complete = association['context_matched'] and not missing and not extra
    return {
        'schema': 'allowance-code-bytes-report-v1',
        'status': 'bytes_matched' if complete else 'incomplete_byte_context',
        'bytes_matched': complete,
        **{key: association[key] for key in ('chain_id', 'token', 'token_address', 'block_number',
           'block_hash', 'measured_pair_count', 'active_pair_count', 'active_spender_count',
           'empty_balance_active_pair_count', 'pairs', 'missing_active_spenders', 'extra_code_spenders')},
        'missing_byte_spenders': missing, 'extra_byte_spenders': extra,
        'recomputed_spenders': [{'spender': s, **v} for s, v in sorted(by_spender.items())],
        'sources': {'runtime_report': runtime['source'], 'raw_code': evidence['source']},
        'complete_wallet_audit': False,
        'input_sha256': {**association['input_sha256'], 'bytes': context.digest(evidence)},
        'limitations': [
            'Recomputed SHA-256 binds bytes to reported hashes; RPC returns and block headers are still unauthenticated.',
            'This is not an Ethereum account proof, code-behavior audit, permission approval or transaction authority.',
            'Only measured standard ERC-20 pairs at this historical block are covered; current state and undiscovered authorizations remain unknown.',
            'Empty balances and empty code never revoke a nonzero allowance; pair exposure bounds overlap per owner.',
            'Proxy targets, delegated code, precompiles, controllers and future execution are not resolved.',
        ],
    }


class CodeRPC(lens.RPC):
    METHODS = {'eth_chainId', 'eth_getBlockByNumber', 'eth_getCode'}

    def call(self, method, params):
        # Parent transport disables environment-derived proxies and redirects.
        return super().call(method, params)


def capture(observation, runtime, endpoint):
    require(endpoint in lens.PUBLIC_ENDPOINTS, 'use a documented public Ethereum endpoint')
    association = context.check(observation, runtime)
    require(association['context_matched'], 'capture requires complete runtime context')
    rpc = CodeRPC(endpoint)
    require(rpc.call('eth_chainId', []) == '0x1', 'expected Ethereum mainnet')
    selector = hex(association['block_number'])
    first = lens.header(rpc.call('eth_getBlockByNumber', [selector, False]))
    require(first['hash'] == association['block_hash'] and first['number'] == selector,
            'permission block is not canonical at this provider')
    reads = []
    for spender in sorted(context.code.validate(runtime)['spenders']):
        params = [spender, {'blockHash': association['block_hash'], 'requireCanonical': True}]
        result = rpc.call('eth_getCode', params)
        bytecode(result)
        reads.append({'method': 'eth_getCode', 'params': params, 'result': result})
    last = lens.header(rpc.call('eth_getBlockByNumber', [selector, False]))
    evidence = {'schema': SCHEMA, 'source': endpoint,
                **{k: association[k] for k in ('chain_id', 'token', 'token_address', 'block_number', 'block_hash')},
                'headers': [first, last], 'reads': reads}
    require(check(observation, runtime, evidence)['bytes_matched'], 'capture did not match')
    require(len(json.dumps(evidence).encode()) <= gate.LIMIT, 'capture exceeds 96 KiB')
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation')
    parser.add_argument('--runtime')
    parser.add_argument('--bytes', dest='evidence')
    parser.add_argument('--capture', action='store_true', help='bounded public read-only code capture')
    parser.add_argument('--endpoint', default=lens.PUBLIC_RPC, choices=sorted(lens.PUBLIC_ENDPOINTS))
    parser.add_argument('--timeout', type=float, default=45)
    parser.add_argument('--save', help='new workspace JSON for a successful capture')
    args = parser.parse_args(argv)
    try:
        require((args.observation is None) == (args.runtime is None), 'supply both observation and runtime')
        require(not (args.capture and args.evidence), '--bytes conflicts with --capture')
        require(args.capture or not args.save, '--save requires --capture')
        require(args.capture or (args.endpoint == lens.PUBLIC_RPC and args.timeout == 45),
                'endpoint and timeout require capture')
        require(1 <= args.timeout <= 55, 'timeout must be 1..55 seconds')
        observation, runtime = (context.demo_inputs() if args.observation is None else
                                (gate.load(args.observation), gate.load(args.runtime)))
        if args.capture:
            evidence = lens.run_bounded(capture, (observation, runtime, args.endpoint), timeout=args.timeout)
        else:
            require(args.observation is None or args.evidence is not None, 'custom inputs need --bytes or --capture')
            evidence = gate.load(args.evidence or HERE / 'zto-code-bytes.json')
        result = check(observation, runtime, evidence)
        if args.save:
            encoded = json.dumps(evidence, indent=2) + '\n'
            require(len(encoded.encode()) <= gate.LIMIT, 'capture exceeds 96 KiB')
            with lens.workspace_path(args.save).open('x', encoding='utf-8') as stream:
                stream.write(encoded)
        print(json.dumps(result, indent=2))
        return 0 if result['bytes_matched'] else 3
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError, RecursionError, TimeoutError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
