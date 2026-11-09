"""The supplementary identifier baseline cannot exploit hidden labels or future calls."""
import copy

from swarm_oversight.exploratory_v21_identifier import VisibleIdentifier, identifiers


def test_identifier_extraction_reads_nested_values_with_exact_boundaries():
    key = 'job_012345abcdef'
    assert identifiers({'record': {'job': key}, 'paths': [f'jobs/{key}.py', 2]}) == {key}
    assert identifiers({'job_012345abcdef': 2}) == set()
    assert identifiers(key + '0') == set()
    assert identifiers('other' + key) == set()


def test_identifier_groups_are_prefix_only_and_ignore_hidden_and_root_fields():
    key = 'job_012345abcdef'
    events = [{'args': {'record': {'job': key}}}, {'args': {'path': 'shared/ops/runbook.md'}, 'root_id': key},
              {'args': {'script_path': f'jobs/{key}.py'}}, {'args': {'job': 'job_abcdef012345'}},
              {'args': {'artifact': f'data/{key}.json'}}]
    mapper = VisibleIdentifier(events, 9)
    assert mapper.group(1) == [1] and mapper.group(2) == [0, 2]
    assert mapper.group(4) == [0, 2, 4]
    assert VisibleIdentifier(events, 2).group(4) == [2, 4]
    changed = copy.deepcopy(events)
    for event in changed:
        event.update(episode_id=key, task_id=key, family=key, attack=key, is_attack=True)
    assert all(VisibleIdentifier(changed, 9).group(i) == mapper.group(i) for i in range(len(events)))
