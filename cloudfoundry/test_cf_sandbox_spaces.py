import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name('cf-sandbox-spaces.py')
SPEC = importlib.util.spec_from_file_location('cf_sandbox_spaces', SCRIPT_PATH)
cf_sandbox_spaces = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cf_sandbox_spaces)


class AnalyzeTest(unittest.TestCase):
    def write_input(self, directory, rows, headers=cf_sandbox_spaces.INPUT_COLUMNS):
        input_file = directory / 'sandbox-spaces.csv'
        with input_file.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(headers)
            writer.writerows(rows)
        return input_file

    def read_csv(self, path):
        with path.open(newline='', encoding='utf-8') as csv_file:
            return list(csv.reader(csv_file))

    def test_analyze_writes_monthly_all_and_non_gsa_reports(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            input_file = self.write_input(directory, [
                ('sandbox-gsa', 'gsa-space', '2024-10-31T23:00:00Z'),
                ('sandbox-client', 'client-one', '2024-10-01T00:00:00Z'),
                ('sandbox-client', 'client-two', '2024-11-02T00:00:00+00:00'),
            ])

            cf_sandbox_spaces.analyze(input_file)

            self.assertEqual(
                self.read_csv(directory / 'all-sandboxes.csv'),
                [['month/year', 'creations'], ['2024/10/1', '2'], ['2024/11/1', '1']],
            )
            self.assertEqual(
                self.read_csv(directory / 'non-gsa-sandboxes.csv'),
                [['month/year', 'creations'], ['2024/10/1', '1'], ['2024/11/1', '1']],
            )
            for report_name in ('all-sandboxes', 'non-gsa-sandboxes'):
                for period_name in ('all-time', 'last-24-months'):
                    chart = directory / f'{report_name}-{period_name}.png'
                    self.assertTrue(chart.is_file())
                    self.assertGreater(chart.stat().st_size, 0)

    def test_analyze_rejects_unexpected_headers(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            input_file = self.write_input(directory, [], headers=('org', 'space', 'date'))

            with self.assertRaisesRegex(ValueError, 'Input CSV must have columns'):
                cf_sandbox_spaces.analyze(input_file)

    def test_analyze_rejects_invalid_creation_date(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            input_file = self.write_input(directory, [
                ('sandbox-client', 'client-space', 'not-a-date'),
            ])

            with self.assertRaisesRegex(ValueError, 'Row 2: Invalid Creation-date'):
                cf_sandbox_spaces.analyze(input_file)


if __name__ == '__main__':
    unittest.main()
