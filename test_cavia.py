import json
import unittest

from cavia import decide, greedy_allocation, improved_allocation, targeted_asks
from kit import HARD, OPTIONS, SOFT, Simulator, eligibility, generate


def member(name, age, gender, wants, *, available=True, missing_hard=False):
    fields = {
        'age_min': 18,
        'age_max': 65,
        'who_to_meet': wants,
        'relationship_structure': 'monogamous',
        'smoking': 'no',
        'partner_smoking': 'any',
        'has_children': False,
        'partner_children': 'any',
        'wants_children': 'unsure',
        'acceptable_zones': ['zone_a'],
        'schedule': ['weekend_day'],
    }
    fields.update({key: values[0] for key, values in OPTIONS.items()})
    statuses = {key: 'observed' for key in fields}
    observed = {key: 0 for key in fields}
    if missing_hard:
        for key in HARD:
            fields[key] = None
            statuses[key] = 'not_asked'
            observed[key] = None
    return {
        'member_id': name,
        'pool_id': 'test',
        'synthetic': True,
        'age': age,
        'gender': gender,
        'zone': 'zone_a',
        'arrived_day': 0,
        'available': available,
        'fields': fields,
        'field_status': statuses,
        'field_observed_day': observed,
        'source': 'test',
    }


def state(members, day=0, budget=12):
    return {
        'schema_version': '1.0.0',
        'synthetic': True,
        'day': day,
        'ask_budget_remaining': budget,
        'members': members,
        'introductions': [],
        'feedback': [],
        'ask_log': [],
    }


class CaviaTests(unittest.TestCase):
    def test_empty_state(self):
        empty = state([])
        self.assertEqual(decide({'phase': 'ask', 'state': empty, 'memory': None})['asks'], [])
        self.assertEqual(decide({'phase': 'match', 'state': empty, 'memory': None})['pairs'], [])

    def test_targeted_asks_respect_budget_and_are_deterministic(self):
        members = [member(f'm{i}', 25 + i, 'woman' if i % 2 else 'man', ['woman', 'man'], missing_hard=True)
                   for i in range(8)]
        current = state(members, budget=7)
        first = targeted_asks(current)
        second = targeted_asks(current)
        self.assertEqual(first, second)
        self.assertLessEqual(len(first) * 3, 7)
        self.assertEqual(len({ask['member_id'] for ask in first}), len(first))

    def test_matching_is_feasible_non_overlapping_and_deterministic(self):
        sim = Simulator(generate(71, 80))
        for _ in range(12):
            observed = sim.observe()
            asks = decide({'phase': 'ask', 'state': observed, 'memory': None})['asks']
            sim.resolve_asks(asks)
            observed = sim.observe()
            request = {'phase': 'match', 'state': observed, 'memory': None}
            first = decide(request)['pairs']
            second = decide(request)['pairs']
            self.assertEqual(first, second)
            used = set()
            by_id = {item['member_id']: item for item in observed['members']}
            for left, right in first:
                self.assertNotIn(left, used)
                self.assertNotIn(right, used)
                self.assertEqual(eligibility(by_id[left], by_id[right])['status'], 'feasible')
                used.update((left, right))
            sim.advance(first)

    def test_two_edge_exchange_improves_total(self):
        edges = {
            ('a', 'b'): 0.90,
            ('c', 'd'): 0.05,
            ('a', 'd'): 0.65,
            ('b', 'c'): 0.65,
        }
        greedy = greedy_allocation(edges)
        improved = improved_allocation(edges)
        self.assertEqual(greedy, [('a', 'b'), ('c', 'd')])
        self.assertEqual(improved, [('a', 'd'), ('b', 'c')])
        self.assertGreater(sum(edges[pair] for pair in improved), sum(edges[pair] for pair in greedy))

    def test_memory_is_small_and_finite_json(self):
        current = state([
            member('a', 27, 'woman', ['man']),
            member('b', 29, 'man', ['woman']),
        ])
        response = decide({'phase': 'match', 'state': current, 'memory': None})
        encoded = json.dumps(response['memory'], allow_nan=False).encode()
        self.assertLess(len(encoded), 1024)

    def test_declined_hard_answer_is_not_asked_again(self):
        person = member('a', 27, 'woman', ['man'], missing_hard=True)
        person['field_status']['schedule'] = 'declined'
        other = member('b', 29, 'man', ['woman'])
        self.assertEqual(targeted_asks(state([person, other])), [])


if __name__ == '__main__':
    unittest.main()
