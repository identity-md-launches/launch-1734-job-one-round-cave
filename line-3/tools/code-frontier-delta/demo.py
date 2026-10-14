"""Real saved ZTO endpoint comparison, then same-block IMD evidence expansion."""
import json
from pathlib import Path
import code_frontier_delta as tool

HERE = Path(__file__).resolve().parent


def main():
    read = lambda path: tool.read_json(HERE.parent / path)
    zto = tool.compare(read('code-proof/zto-proof.json'), [],
                       read('code-routes/zto-proof.json'), [])
    imd_source = read('code-routes/imd-proof.json')
    imd = tool.compare(imd_source, [], imd_source,
                       [read('code-target-proofs/imd-target-proof.json')])
    passed = (zto['decision'] == 'same-bounded-scan'
              and zto['comparison_mode'] == 'historical-endpoint-comparison'
              and zto['block_distance'] == 2929
              and imd['comparison_mode'] == 'same-block-evidence-comparison'
              and imd['decision'] == 'bounded-scan-differences'
              and len(imd['runtime_evidence']['only_after_scan']) == 1
              and len(imd['missing_constant_targets']['only_before_scan']) == 1
              and imd['after']['missing_constant_targets'] == []
              and imd['before']['unresolved_call_site_count'] == 11
              and imd['after']['unresolved_call_site_count'] == 34
              and len(imd['unresolved_sites']['only_after_scan']) == 23
              and imd['unresolved_sites']['unchanged_count'] == 11)
    return {'demonstration_passed': passed, 'ZTO': zto, 'IMD': imd,
            'evidence': 'Saved real historical proofs; no network call or independently authenticated anchor.'}


if __name__ == '__main__':
    report = main()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['demonstration_passed'] else 1)
