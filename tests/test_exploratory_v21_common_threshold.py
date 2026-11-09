"""POST-HOC EXPLORATORY counterfactual accounting, paired inference and tied-score checks."""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[1]/'scripts/exploratory_v21_common_threshold.py'
SPEC = importlib.util.spec_from_file_location('common_threshold_tests', PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_calibration_support_not_sparse_backoff_and_empty_bin_behavior():
    scores = np.array([[1., 8.], [2., 9.], [7., 1.], [8., 2.]])
    sizes = np.array([[1, 1], [1, 1], [4, 4], [4, 4]])
    table, support, backoff = MODULE.policy_tables(scores, sizes, .5, 'size_bin', minimum=2)
    np.testing.assert_allclose(table, [[1.5, 4.5, 7.5], [8.5, 5., 1.5]])
    assert support.tolist() == [[2, 0, 2], [2, 0, 2]]
    assert backoff.tolist() == [[False, True, False]]*2
    global_table, _, global_backoff = MODULE.policy_tables(scores, sizes, .5, 'global')
    np.testing.assert_allclose(global_table, [[4.5]*3, [5.]*3])
    assert not global_backoff.any()
    with pytest.raises(ValueError):
        MODULE.policy_tables(scores, sizes*0, .5, 'global')


def test_common_pool_excludes_supplement_and_requires_size_one_singletons():
    scores = np.tile(np.arange(6, dtype=float), (4, 1))
    sizes = np.ones_like(scores, dtype=int)
    np.testing.assert_allclose(MODULE.common_cutoffs(scores, sizes, .5), [0., 2.])
    scores[:, 5] = 900
    np.testing.assert_allclose(MODULE.common_cutoffs(scores, sizes, .5), [0., 2.])
    sizes[:, 0] = 2
    with pytest.raises(ValueError):
        MODULE.common_cutoffs(scores, sizes, .5)


def test_strict_ties_and_later_flags_do_not_double_count_streams():
    scores = np.array([[[[5., 6., 1.]], [[6., 6., 5.]], [[1., 2., 3.]]]])
    sizes = np.ones_like(scores, dtype=int)
    flags = MODULE.piece_flags(scores, sizes, np.full((1, 3), 5.))
    assert flags.tolist() == [[[[False, True, False]], [[True, True, False]], [[False]*3]]]
    np.testing.assert_allclose(MODULE.flag_rates(flags), [[2/3, 1/3, 2/3, 1/3]])
    with pytest.raises(ValueError):
        MODULE.flag_rates(flags[..., :2])
    with pytest.raises(ValueError):
        MODULE.piece_flags(scores, sizes, np.zeros((2, 3)))


def test_decomposition_subtracts_baseline_allocation_and_closes_with_signed_effects():
    result = MODULE.decompose(np.array([.8, .2]), np.array([.5, .4]),
                              np.array([.6, .3]), np.array([.4, .1]))
    np.testing.assert_allclose(result, [[.3, .2, .1], [-.2, .2, -.4]])
    np.testing.assert_allclose(result[:, 0], result[:, 1]+result[:, 2])


def test_curve_strict_thresholds_include_ties_and_complete_endpoints():
    curve = MODULE.score_curve(np.array([1., 1., 3.]), np.array([[2., 0., 0.], [0., 3., 0.]]))
    assert curve['cost'][0] == 0 and curve['cost'][-1] == 1
    np.testing.assert_array_equal(curve['catch'][0], [0, 0])
    np.testing.assert_array_equal(curve['catch'][-1], [1, 1])
    at_one = np.flatnonzero(curve['threshold'] == 1)[0]
    assert curve['cost'][at_one] == pytest.approx(1/3)
    np.testing.assert_allclose(curve['catch'][at_one], [1., .5])
    with pytest.raises(ValueError):
        MODULE.score_curve(np.array([]), np.ones((2, 3)))


def test_interpolation_uses_last_vertical_point_and_reports_mixture_not_extrapolation():
    curve = {'cost': np.array([0., 0., .2, 1.]),
             'catch': np.array([[0., 0.], [.4, .2], [.8, .6], [1., 1.]])}
    point = MODULE.interpolate_curve(curve, np.array([0., .1, 1.]))
    np.testing.assert_allclose(point['rates'], [[.4, .2], [.6, .4], [1., 1.]])
    assert point['lower'].tolist() == [1, 1, 3]
    assert point['upper'].tolist() == [1, 2, 3]
    assert point['weight'][1] == .5
    with pytest.raises(ValueError):
        MODULE.interpolate_curve(curve, np.array([1.1]))


def test_curve_relation_checks_crossings_at_union_of_knots():
    a = {'cost': np.array([0., .05, .1, 1.]), 'catch': np.array([[0., 0.], [.2, .2], [.9, .9], [1., 1.]])}
    b = {'cost': np.array([0., .04, .1, 1.]), 'catch': np.array([[0., 0.], [.3, .3], [.6, .6], [1., 1.]])}
    assert MODULE.curve_relation(a, b)['all_pieces']['relation'] == 'cross'
    assert MODULE.curve_relation(a, a)['all_pieces']['relation'] == 'coincide'


def test_attainable_cost_is_not_mislabeled_as_a_mixture_due_to_float_rounding():
    for rounded in [1-1764/1800, np.nextafter(.02, 0)]:
        curve = {'cost': np.array([0., rounded, 1.]),
                 'catch': np.array([[0., 0.], [.5, .5], [1., 1.]])}
        point = MODULE.interpolate_curve(curve, np.array([.02]))
        np.testing.assert_array_equal(point['lower'], [1])
        np.testing.assert_array_equal(point['upper'], [1])
        np.testing.assert_allclose(point['rates'], [[.5, .5]])


def test_later_statistics_pair_same_piece_and_preserve_task_blocks():
    differences = np.array([[[1., -1.]]*3, [[3., 5.]]*3])
    np.testing.assert_allclose(MODULE.later_statistics(differences), [[2., 2.], [2., 2.], [2., 2.]])
    repeated_first_task = differences[[0, 0]]
    np.testing.assert_allclose(MODULE.later_statistics(repeated_first_task), [[1., 1.], [-1., -1.], [0., 0.]])
    with pytest.raises(ValueError):
        MODULE.later_statistics(np.zeros((2, 3, 3)))


def test_network_guard_rejects_socket_events_without_using_credentials():
    MODULE.deny_network('open', ())
    with pytest.raises(PermissionError):
        MODULE.deny_network('socket.__new__', ())


def test_effect_text_preserves_negative_intervals_and_rejects_invalid_values():
    assert MODULE.effect_text(-.1, np.array([-.2, .05])) == '-10.00 [-20.00, 5.00]'
    assert MODULE.effect_text(2., np.array([1., 3.]), 1) == '2.00 [1.00, 3.00]'
    with pytest.raises(ValueError):
        MODULE.effect_text(0., np.array([1., -1.]))
    with pytest.raises(ValueError):
        MODULE.effect_text(float('nan'), np.array([0., 1.]))


def test_paired_bootstrap_and_evaluation_keep_identical_maps_identical():
    pieces = np.tile(np.array([[[[1., 2., 3.]]*6]]), (2, 3, 1, 1))
    cal = np.tile(np.arange(9, dtype=float)[:, None], (1, 6))
    groups = [np.array([i]) for i in range(9)]
    data = MODULE.FamilyData('fixture', (*MODULE.PRIMARY_MAPS, 'identifier'), [1, 2], pieces,
                             np.ones_like(pieces, dtype=int), cal, np.ones_like(cal, dtype=int),
                             cal, np.ones_like(cal, dtype=int), groups, groups)
    result = MODULE.paired_bootstrap([data], 8, 20261108)['fixture']
    np.testing.assert_allclose(result['decomposition']['estimate'], 0)
    np.testing.assert_allclose(result['decomposition']['ci'], 0)
    np.testing.assert_allclose(result['later_scores']['estimate'], 0)
    again = MODULE.paired_bootstrap([data], 8, 20261108)['fixture']
    for key in result:
        np.testing.assert_array_equal(result[key]['ci'], again[key]['ci'])
