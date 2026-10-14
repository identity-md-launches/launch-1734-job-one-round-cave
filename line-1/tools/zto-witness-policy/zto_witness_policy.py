#!/usr/bin/env python3
"""Apply a receiver's explicit source/provider policy to saved ZTO witnesses."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'zto-witness-replay'))
import zto_witness_replay as replay

require = replay.require
KEYS = {'schema', 'expected_block_hash', 'reference_block', 'max_age_blocks',
        'input_token', 'maximum_input_raw', 'maximum_slippage_bps', 'sources'}


def validate_policy(policy):
    require(type(policy) is dict and set(policy) == KEYS, 'unexpected policy fields')
    require(policy['schema'] == 'zto-witness-policy-v1', 'unexpected policy schema')
    require(type(policy['expected_block_hash']) is str and
            re.fullmatch(r'0x[0-9a-f]{64}', policy['expected_block_hash']) is not None,
            'policy block hash must be lowercase bytes32')
    for key in ('reference_block', 'max_age_blocks'):
        require(type(policy[key]) is int and 0 <= policy[key] < 1 << 64,
                'policy ' + key + ' must be uint64')
    require(type(policy['input_token']) is str and policy['input_token'] in ('ZTO', 'IMD'),
            'policy input token must be ZTO or IMD')
    raw = policy['maximum_input_raw']
    require(type(raw) is str and re.fullmatch(r'[1-9][0-9]{0,38}', raw) is not None and
            int(raw) < 1 << 127, 'policy maximum input must be positive int128 decimal string')
    tolerance = policy['maximum_slippage_bps']
    require(type(tolerance) is int and 0 <= tolerance <= 9999, 'policy slippage must be 0..9999')
    sources = policy['sources']
    require(type(sources) is dict and 1 <= len(sources) <= 16, 'policy needs 1..16 source labels')
    for label, group in sources.items():
        require(type(label) is str, 'policy source label must be a string')
        replay.path.z.validate_endpoint(label)
        require(type(group) is str and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', group) is not None,
                'provider group must be canonical lowercase identifier')
    return policy


def review(first, second, check_a, check_b, policy, token, amount, slippage_bps):
    validate_policy(policy)
    # Never trust a precomputed witness report or derive receiver policy from it.
    result = replay.replay(first, second, check_a, check_b, token, amount, slippage_bps,
                           policy['expected_block_hash'], policy['reference_block'],
                           policy['max_age_blocks'])
    state, _, _ = replay.path.decode(first)
    raw = replay.path.z.parse_amount(amount, state['decimals'][1 if token == 'ZTO' else 0])
    reasons = list(result['reasons'])
    if token != policy['input_token']:
        reasons.append('input_token_outside_receiver_policy')
    elif raw > int(policy['maximum_input_raw']):
        reasons.append('input_exceeds_receiver_ceiling')
    if slippage_bps > policy['maximum_slippage_bps']:
        reasons.append('slippage_exceeds_receiver_ceiling')
    groups = [policy['sources'].get(label) for label in result['source_labels']]
    if any(group is None for group in groups):
        reasons.append('source_not_approved_by_receiver')
    elif groups[0] == groups[1]:
        reasons.append('same_receiver_provider_group')
    released = not reasons and result['bound_released']
    return {'schema': 'zto-witness-policy-report-v1',
            'status': 'accepted' if released else 'withheld',
            'chain_id': 1, 'pool_id': result['pool_id'], 'block': result['block'],
            'source_labels': result['source_labels'], 'receiver_provider_groups': groups,
            'receiver_policy_sha256': replay.digest(policy),
            'input_token': token, 'requested_input': amount, 'input_raw': str(raw),
            'slippage_bps': slippage_bps, 'reasons': reasons,
            'bound_released': released, 'bound': result['bound'] if released else None,
            'evidence_sha256': result['evidence_sha256'],
            'replay_status': result['status'], 'raw_quoter_matches': result['raw_quoter_matches'],
            'age_blocks': result['age_blocks'],
            'limitations': ['Provider groups are receiver assertions, not authenticated upstream identities.',
                            'Copied evidence relabeled as two approved groups can still pass.',
                            *replay.LIMITATIONS]}


def demo():
    observation, check = replay.demo_inputs()
    policy = {'schema': 'zto-witness-policy-v1',
              'expected_block_hash': observation['base']['block']['hash'],
              'reference_block': int(observation['base']['block']['number'], 16),
              'max_age_blocks': 0, 'input_token': 'ZTO',
              'maximum_input_raw': str(10**18), 'maximum_slippage_bps': 100,
              'sources': {observation['base']['source']: 'archived-publicnode'}}
    result = review(observation, observation, check, check, policy, 'ZTO', '1', 100)
    result['mode'] = 'offline_real_historical_single_source'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    for key in ('snapshot-a', 'snapshot-b', 'quoter-a', 'quoter-b', 'policy'):
        parser.add_argument('--' + key)
    parser.add_argument('--input', choices=('ZTO', 'IMD'))
    parser.add_argument('--amount')
    parser.add_argument('--slippage-bps', type=int)
    args = parser.parse_args(argv)
    values = [getattr(args, key) for key in ('snapshot_a', 'snapshot_b', 'quoter_a',
              'quoter_b', 'policy', 'input', 'amount', 'slippage_bps')]
    try:
        if args.demo:
            require(all(v is None for v in values), '--demo cannot be combined with inputs')
            result = demo()
        else:
            require(all(v is not None for v in values), 'supply four evidence paths, receiver policy and candidate controls')
            result = review(*(replay.read_json(v) for v in values[:5]), *values[5:])
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if args.demo or result['bound_released'] else 2
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
