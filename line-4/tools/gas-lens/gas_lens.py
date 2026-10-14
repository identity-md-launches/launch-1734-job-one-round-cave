#!/usr/bin/env python3
"""Measure gas for an exact, hash-pinned historical Ethereum call. Read-only."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'call-changes'))
import call_changes as changes

core = changes.core
SCHEMA = 'gas-lens-v1'
LIMIT = 95_000
LIMITS = ('Provider-reported historical eth_estimateGas, not actual gas consumed. '
          'The provider chooses unspecified gas and fee context; its estimate may change '
          'with state, block, sender funds or client behavior. Saved RPC claims and headers '
          'are not authenticated. A matching limit does not establish execution, safety, '
          'authorization, future inclusion or an appropriate transaction gas limit. '
          'No transaction is signed or sent.')


class GasRPC(core.RPC):
    METHODS = core.RPC.METHODS | {'eth_estimateGas'}


def positive_decimal(value):
    core.require(isinstance(value, str) and value.isascii() and
                 value.isdecimal() and len(value) <= 20 and
                 (value == '0' or not value.startswith('0')),
                 'max gas must be canonical decimal')
    number = int(value)
    core.require(0 < number < 2**64, 'max gas must be between 1 and 2^64-1')
    return number


def check_bundle(value):
    core.require(isinstance(value, dict) and
                 set(value) == {'schema', 'observation', 'estimate', 'recheck'} and
                 value['schema'] == SCHEMA, 'invalid gas evidence bundle')
    observation = value['observation']
    validated = changes.validate(observation)
    block = core.header(observation['block'])
    core.require(isinstance(value['recheck'], dict) and
                 set(value['recheck']) == {'number', 'hash', 'timestamp'} and
                 core.header(value['recheck']) == block,
                 'rechecked header differs from call block')
    estimate = value['estimate']
    core.require(isinstance(estimate, dict) and len(estimate) == 1,
                 'estimate must contain exactly result or error')
    if 'result' in estimate:
        gas = core.quantity(estimate['result'])
        core.require(0 < gas < 2**64, 'gas estimate is outside the supported range')
    else:
        core.require('error' in estimate, 'missing gas estimate outcome')
        error = core.RPCError(estimate['error']).error
        core.require(set(error) <= {'code', 'message', 'data'}, 'unknown gas RPC error field')
        if 'data' in error:
            core.data(error['data'])
        gas = None
    return validated, gas, block


def evaluate(value, max_gas=None):
    checked, gas, block = check_bundle(value)
    cap = positive_decimal(max_gas) if max_gas is not None else None
    observation = value['observation']
    result = checked['result']
    report = {
        'schema': SCHEMA, 'verdict': 'inconclusive', 'source': observation['source'],
        'chain_id': 1, 'block': block, 'call': checked['call'],
        'call_status': result['status'], 'estimate_gas': str(gas) if gas is not None else None,
        'max_gas': str(cap) if cap is not None else None,
        'limits': LIMITS,
    }
    if gas is None:
        report['reason'] = 'provider did not return a gas estimate'
    elif result['status'] not in {'returned', 'returned_true'}:
        report['reason'] = 'rehearsed call did not return a usable result'
    elif cap is None:
        report.update(verdict='measured', reason='provider supplied a gas estimate; no limit was supplied')
    elif gas <= cap:
        report.update(verdict='within_limit', reason='provider estimate is no more than the supplied limit')
    else:
        report.update(verdict='above_limit', reason='provider estimate exceeds the supplied limit')
    return report


def capture(rpc, tx, returns, block='finalized'):
    observation = changes.capture(rpc, tx, returns, block)
    chosen = core.header(observation['block'])
    pin = {'blockHash': chosen['hash'], 'requireCanonical': True}
    try:
        estimate = {'result': rpc.call('eth_estimateGas', [observation['call'], pin])}
    except core.RPCError as exc:
        estimate = {'error': exc.error}
    recheck = core.header(rpc.call('eth_getBlockByNumber', [chosen['number'], False]))
    bundle = {'schema': SCHEMA, 'observation': observation,
              'estimate': estimate, 'recheck': recheck}
    check_bundle(bundle)
    return bundle


def encoded(value):
    check_bundle(value)
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    core.require(len(raw) <= LIMIT, 'gas evidence bundle exceeds 95 KB')
    return raw


def load(path):
    with core.workspace_path(path).open('rb') as handle:
        raw = handle.read(LIMIT + 1)
    core.require(len(raw) <= LIMIT, 'gas evidence bundle exceeds 95 KB')
    value = json.loads(raw, object_pairs_hook=changes.no_duplicates,
                       parse_constant=changes.reject_constant)
    check_bundle(value)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    demo = commands.add_parser('demo', help='replay saved real ZTO gas evidence offline')
    demo.add_argument('--max-gas', help='reviewer-supplied decimal gas limit')
    replay = commands.add_parser('replay', help='replay a saved gas evidence bundle')
    replay.add_argument('bundle')
    replay.add_argument('--max-gas', help='reviewer-supplied decimal gas limit')
    live = commands.add_parser('live', help='read-only public RPC rehearsal and gas estimate')
    live.add_argument('--token', choices=core.TOKENS, default='ZTO')
    live.add_argument('--from-observation', help='repeat this saved exact call and return type')
    live.add_argument('--rpc', choices=core.ENDPOINTS, default=core.ENDPOINTS[0])
    live.add_argument('--block', default='finalized',
                      help='finalized or a canonical hexadecimal finalized height')
    live.add_argument('--max-gas', help='reviewer-supplied decimal gas limit')
    live.add_argument('--save', help='create a new workspace-contained bundle; never overwrite')
    args = parser.parse_args(argv)
    try:
        if args.mode == 'demo':
            bundle = load(HERE / 'zto-gas-evidence.json')
        elif args.mode == 'replay':
            bundle = load(args.bundle)
        else:
            destination = core.workspace_path(args.save) if args.save else None
            if destination:
                core.require(destination.parent.is_dir() and not destination.exists(),
                             'save requires an existing parent and a new file')
            if args.from_observation:
                baseline = changes.load_observation(args.from_observation)
                tx, returns = baseline['call'], baseline['returns']
            else:
                tx = {'to': core.TOKENS[args.token], 'data': '0x18160ddd', 'value': '0x0'}
                returns = 'uint256'
            # Check a supplied policy before making any network request.
            if args.max_gas is not None:
                positive_decimal(args.max_gas)
            bundle = capture(GasRPC(args.rpc), tx, returns, changes.block_selector(args.block))
            if destination:
                with destination.open('xb') as handle:
                    handle.write(encoded(bundle))
        report = evaluate(bundle, args.max_gas)
        print(json.dumps(report, indent=2, allow_nan=False))
        return {'measured': 0, 'within_limit': 0, 'above_limit': 1,
                'inconclusive': 2}[report['verdict']]
    except (ValueError, KeyError, TypeError, OSError, RecursionError, core.RPCError) as exc:
        print(json.dumps({'schema': SCHEMA, 'verdict': 'inconclusive', 'error': str(exc)}),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
