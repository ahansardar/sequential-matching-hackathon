"""Reference policy: executable JSON adapter, never reads simulator hidden state."""
import argparse
import itertools
import json
import random
import sys
from adaptive import decide as decide_adaptive
from kit import baseline_asks, baseline_match, eligibility


def decide(request, mode='greedy'):
    if mode.startswith('adaptive'):
        return decide_adaptive(request, mode)
    state = request['state']
    memory = request.get('memory') or {}
    if request['phase'] == 'ask':
        return {'asks': [] if mode == 'no_asks' else baseline_asks(state), 'memory': memory}
    if mode != 'random':
        pairs = baseline_match(state)
    else:
        candidates = [m for m in state['members'] if m['available']]
        past = {tuple(sorted((i['user_a'], i['user_b']))) for i in state['introductions']}
        edges = [tuple(sorted((a['member_id'], b['member_id'])))
                 for a, b in itertools.combinations(candidates, 2)
                 if eligibility(a, b)['status'] == 'feasible'
                 and tuple(sorted((a['member_id'], b['member_id']))) not in past]
        random.Random(17 + state['day']).shuffle(edges)
        pairs, used = [], set()
        for pair in edges:
            if not used.intersection(pair):
                pairs.append(list(pair))
                used.update(pair)
    return {'pairs': pairs, 'memory': memory}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--baseline',
        choices=[
            'adaptive', 'adaptive_greedy', 'adaptive_always_max',
            'greedy', 'no_asks', 'random',
        ],
        default='adaptive',
    )
    args = parser.parse_args()
    request = json.load(sys.stdin)
    print(json.dumps(decide(request, args.baseline), allow_nan=False))
