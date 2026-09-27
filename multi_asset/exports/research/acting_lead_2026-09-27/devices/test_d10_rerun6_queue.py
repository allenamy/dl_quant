#!/usr/bin/env python3
"""Synthetic queue safety checks: no pod files, jobs, candidate returns, or writes."""
import unittest

from d10_rerun6_queue import GIB, dependency_state, resources_ready, row_counts


class QueueTest(unittest.TestCase):
    def test_exact_resource_edges(self):
        self.assertTrue(resources_ready(28 * GIB, 4 * GIB, 4 * GIB))
        self.assertFalse(resources_ready(28 * GIB - 1, 0, 9 * GIB))
        self.assertFalse(resources_ready(50 * GIB, 4 * GIB + 1, 9 * GIB))
        self.assertFalse(resources_ready(50 * GIB, 0, 4 * GIB - 1))

    def test_reader_terminal_required(self):
        self.assertEqual(dependency_state('T KSR_DONE series=36\n', True), 'RUNNING')
        self.assertEqual(dependency_state('T KSR_READOUT_WAIT RUNNING\n', False), 'GONE_WITHOUT_MARKER')
        self.assertEqual(dependency_state('T KSR_READOUT_DONE sha=x\n', False), 'DONE')
        self.assertEqual(dependency_state('T explanation KSR_READOUT_DONE\n', True), 'RUNNING')

    def test_failure_has_precedence(self):
        text = 'T KSR_READOUT_DONE sha=x\nT KSR_READOUT_FAILED failure\n'
        self.assertEqual(dependency_state(text, True), 'FAILED')

    def test_unavailable_is_not_success(self):
        for verdict in ['NOT_RUN', 'FAIL', 'DIFFERS', 'ERROR', 'UNKNOWN']:
            with self.subTest(verdict=verdict):
                self.assertFalse(row_counts([{'verdict': verdict}])[1])
        self.assertFalse(row_counts([])[1])
        rows = [{'verdict': v} for v in ['PASS', 'IDENTICAL', 'IDENTICAL_EXCEPT_DECLARED']]
        self.assertTrue(row_counts(rows)[1])


if __name__ == '__main__':
    unittest.main()
