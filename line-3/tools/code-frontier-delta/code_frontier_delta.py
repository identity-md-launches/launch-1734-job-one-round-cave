#!/usr/bin/env python3
"""Compare two proof-backed bounded dependency scans without inferring deployment history."""
import argparse
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / 'code-dependency-frontier'))
import code_dependency_frontier as frontier

lens = frontier.targets.calls.lens
require = lens.require
read_json = frontier.read_json


def _index(rows, key):
    result = {}
    for row in rows:
        identity = key(row)
        require(identity not in result, 'duplicate comparison identity')
        result[identity] = row
    return result


def _partition(before, after):
    """Stable ordering; never silently merge different runtime identities at one PC."""
    common = before.keys() & after.keys()
    return {
        'only_before_scan': [before[key] for key in sorted(before.keys() - after.keys())],
        'only_after_scan': [after[key] for key in sorted(after.keys() - before.keys())],
        'changed': [{'before': before[key], 'after': after[key]}
                    for key in sorted(common) if before[key] != after[key]],
        'unchanged_count': sum(before[key] == after[key] for key in common),
    }


def _edge_index(report, nodes):
    rows = []
    for edge in report['constant_edges']:
        target = nodes.get(edge['target'])
        rows.append({**edge, 'caller_code_hash': nodes[edge['caller']]['code_hash'],
                     'target_code_hash': target['code_hash'] if target else None})
    return _index(rows, lambda row: (row['caller'], row['caller_code_hash'], row['target']))


def _unresolved_index(report, nodes):
    rows = [{'caller': group['caller'],
             'caller_code_hash': nodes[group['caller']]['code_hash'], **site}
            for group in report['unresolved_calls'] for site in group['sites']]
    return _index(rows, lambda row: (row['caller'], row['caller_code_hash'],
                                    row['pc'], row['opcode']))


def _snapshot(report, anchor):
    return {'code_block': report['code_block'],
            'decision': report['decision'],
            'proof_bundle_roots': sorted(lens.address(root)
                                         for root in report['proof_bundle_roots']),
            'proved_runtime_count': report['proved_runtime_count'],
            'constant_edge_count': report['constant_edge_count'],
            'missing_constant_targets': report['missing_constant_targets'],
            'unresolved_call_site_count': report['unresolved_call_site_count'],
            'caller_supplied_anchor_hash_matched': anchor is not None}


def _canonical_root(bundle):
    """Case normalization is not new evidence; avoid mutating the caller's bundle."""
    observation = {**bundle['observation'],
                   'target': lens.address(bundle['observation']['target'])}
    return {**bundle, 'observation': observation}


def _scan(source, targets, anchor):
    require(isinstance(targets, list) and len(targets) <= 16,
            'at most 16 target proofs per side')
    return frontier.evaluate(_canonical_root(source),
                             [_canonical_root(bundle) for bundle in targets], anchor)


def compare(before_source, before_targets, after_source, after_targets,
            before_anchor=None, after_anchor=None):
    """Raw bundles only: neither scan nor a saved success flag is accepted as proof."""
    before = _scan(before_source, before_targets, before_anchor)
    after = _scan(after_source, after_targets, after_anchor)
    require(lens.address(before['source_target']) == lens.address(after['source_target']),
            'different source targets')
    old_block, new_block = before['code_block'], after['code_block']
    old_height, new_height = (lens.quantity(block['number'])
                              for block in (old_block, new_block))
    require(new_height >= old_height, 'after block precedes before block')
    if new_height == old_height:
        require(new_block['hash'] == old_block['hash'],
                'equal block heights have different hashes')
        mode = 'same-block-evidence-comparison'
    else:
        mode = 'historical-endpoint-comparison'

    old_nodes = _index(before['runtimes'], lambda row: row['address'])
    new_nodes = _index(after['runtimes'], lambda row: row['address'])
    runtime_changes = _partition(old_nodes, new_nodes)
    # Raw state proofs at one commitment cannot justify conflicting code identities.
    if mode == 'same-block-evidence-comparison':
        require(not runtime_changes['changed'], 'conflicting same-block runtime identities')
    edges = _partition(_edge_index(before, old_nodes), _edge_index(after, new_nodes))
    unresolved = _partition(_unresolved_index(before, old_nodes),
                            _unresolved_index(after, new_nodes))
    require(not unresolved['changed'], 'same runtime/site has conflicting scan details')
    # Report all remaining common unknown operands, so a flat count cannot hide them.
    old_unknown = _unresolved_index(before, old_nodes)
    new_unknown = _unresolved_index(after, new_nodes)
    unresolved['present_in_both_scans'] = [old_unknown[key]
                                           for key in sorted(old_unknown.keys() & new_unknown.keys())]
    del unresolved['changed']
    old_missing, new_missing = (set(report['missing_constant_targets'])
                                for report in (before, after))
    missing = {'only_before_scan': sorted(old_missing - new_missing),
               'only_after_scan': sorted(new_missing - old_missing),
               'present_in_both_scans': sorted(old_missing & new_missing)}
    changed = any(group['only_before_scan'] or group['only_after_scan']
                  or group.get('changed') for group in (runtime_changes, edges, unresolved))
    return {
        'schema': 'code-frontier-delta-v1', 'chain_id': 1,
        'source_target': lens.address(before['source_target']), 'comparison_mode': mode,
        'block_distance': new_height - old_height,
        'decision': 'bounded-scan-differences' if changed else 'same-bounded-scan',
        'before': _snapshot(before, before_anchor), 'after': _snapshot(after, after_anchor),
        'runtime_evidence': runtime_changes, 'constant_edges': edges,
        'missing_constant_targets': missing, 'unresolved_sites': unresolved,
        'raw_proofs_reverified': True,
        'anchor_authenticity_verified': False, 'common_chain_ancestry_verified': False,
        'continuous_stability_verified': False, 'reachability_verified': False,
        'dependency_completeness_verified': False, 'semantic_safety_verified': False,
        'scope': 'Comparison of supplied proof-backed structural scans only. Runtime entries '
                 'present on one side mean evidence entered or left this scan, never newly '
                 'deployed or destroyed code. Site identities include caller address, caller '
                 'runtime hash, PC and opcode; changed runtime hashes do not reuse site '
                 'identities. Fewer missing constant-target proofs may expose more unresolved '
                 'sites. Sites absent from the after scan are not proven resolved or '
                 'unreachable. Equal scans do not prove complete dependencies, safety, '
                 'current state or continuous stability. Different heights do not prove '
                 'common-chain ancestry. Headers, anchors, beacon implementation call '
                 'results, proxy routing and reachability remain unauthenticated. '
                 'No transaction approval is emitted.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-source', required=True, help='workspace-local raw Code Proof JSON')
    parser.add_argument('--after-source', required=True, help='raw proof at same or later block')
    parser.add_argument('--before-target-proof', action='append', default=[])
    parser.add_argument('--after-target-proof', action='append', default=[])
    parser.add_argument('--before-anchor-hash')
    parser.add_argument('--after-anchor-hash')
    args = parser.parse_args()
    try:
        require(len(args.before_target_proof) <= 16 and len(args.after_target_proof) <= 16,
                'at most 16 target proofs per side')
        result = compare(read_json(args.before_source),
                         [read_json(path) for path in args.before_target_proof],
                         read_json(args.after_source),
                         [read_json(path) for path in args.after_target_proof],
                         args.before_anchor_hash, args.after_anchor_hash)
        print(json.dumps(result, indent=2))
        return 3 if result['decision'] == 'bounded-scan-differences' else 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print('Code Frontier Delta: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
