"""Run assignment tests and additional cases with separate totals."""

import os
from pathlib import Path
import sys
import unittest


def main():
    os.chdir(Path(__file__).resolve().parent)
    groups = (
        ('Provided assignment tests', 'test.TestBibTeXGrammar'),
        ('Additional valid inputs', 'tests.test_edge_cases.ValidInputTests'),
        ('Invalid inputs rejected', 'tests.test_edge_cases.InvalidInputTests'),
        ('SynCode parser compatibility', 'tests.test_syncode.SynCodeParserTests'),
    )
    success = True
    for label, name in groups:
        print(f'\n{label}', flush=True)
        suite = unittest.defaultTestLoader.loadTestsFromName(name)
        expected = suite.countTestCases()
        result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
        passed = max(0, result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped))
        print(f'{label}: {passed}/{expected} passed', flush=True)
        success = success and result.wasSuccessful() and not result.skipped
    print('\nOVERALL: ' + ('PASS' if success else 'FAIL'))
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
