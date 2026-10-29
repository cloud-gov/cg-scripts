#!/usr/bin/env python3
description = """
Emit a CSV of spaces belonging to sandbox orgs.

Columns: Org-name, Space-name, Creation-date

Only orgs whose name starts with "sandbox-" are included. Data is retrieved via
the Cloud Foundry v3 API using `cf curl`, so you must be logged in (cf login)
with sufficient visibility (e.g. a global auditor or admin) before running.

CSV is written to stdout.

Use -a/--analyze INPUT.csv to summarize a CSV previously emitted by this
script. The analysis writes all-sandboxes.csv and non-gsa-sandboxes.csv next
to INPUT.csv, with monthly creation totals and four PNG bar charts.
"""

import argparse
import csv
from collections import Counter
from datetime import datetime
import json
import logging
from pathlib import Path
from statistics import median
import subprocess
import sys
from urllib.parse import urlparse

INPUT_COLUMNS = ('Org-name', 'Space-name', 'Creation-date')
OUTPUT_COLUMNS = ('month/year', 'creations')
GSA_SANDBOX_ORG = 'sandbox-gsa'
CHART_PERIODS = {
    'all-time': None,
    'last-24-months': 24,
}

def test_authenticated():
    cmd = "cf oauth-token"
    try:
        result = subprocess.run(
            cmd.split(" "),
            check=True,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as e:
        print(
            f'Error: Command "{cmd}" failed, are you sure you\'re authenticated?',
            file=sys.stderr,
        )
        sys.exit(1)  # Exit with non-zero status cod

def cf_curl(path):
    """Call `cf curl PATH` and return the parsed JSON response."""
    logging.info('getting %s', path)
    output = subprocess.check_output(
        ['cf', 'curl', path], universal_newlines=True
    )
    return json.loads(output)


def paginate(initial_path):
    """Yield every resource across all pages starting at initial_path."""
    path = initial_path
    while path is not None:
        page = cf_curl(path)
        for resource in page['resources']:
            yield resource
        next_link = page['pagination']['next']
        if next_link is None:
            path = None
        else:
            parts = urlparse(next_link['href'])
            path = parts.path + '?' + parts.query


def get_sandbox_orgs():
    """Return a dict of {org_guid: org_name} for orgs named sandbox-*."""
    orgs = {}
    for org in paginate('/v3/organizations?per_page=100'):
        name = org['name']
        if name.startswith('sandbox-'):
            orgs[org['guid']] = name
    return orgs


def get_spaces(org_guids):
    """Yield spaces belonging to the given org guids."""
    if not org_guids:
        return
    guid_filter = ','.join(org_guids)
    path = f'/v3/spaces?per_page=100&organization_guids={guid_filter}'
    for space in paginate(path):
        yield space


def month_start(creation_date):
    """Return a creation date's month as YYYY/M/1, or raise ValueError."""
    normalized_date = creation_date.replace('Z', '+00:00')
    try:
        date = datetime.fromisoformat(normalized_date)
    except ValueError as error:
        raise ValueError(
            f'Invalid Creation-date {creation_date!r}; expected ISO 8601.'
        ) from error
    return f'{date.year}/{date.month}/1'


def creation_counts(input_file, exclude_gsa=False):
    """Count sandbox space creations per month from an emitted CSV file."""
    counts = Counter()
    with input_file.open(newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames != list(INPUT_COLUMNS):
            raise ValueError(
                'Input CSV must have columns: ' + ', '.join(INPUT_COLUMNS)
            )
        for row_number, row in enumerate(reader, start=2):
            if exclude_gsa and row['Org-name'] == GSA_SANDBOX_ORG:
                continue
            try:
                month = month_start(row['Creation-date'])
            except ValueError as error:
                raise ValueError(f'Row {row_number}: {error}') from error
            counts[month] += 1
    return counts


def write_creation_counts(output_file, counts):
    """Write monthly creation counts in chronological order."""
    with output_file.open('w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(OUTPUT_COLUMNS)
        for month in sorted(counts, key=lambda value: datetime.strptime(value, '%Y/%m/%d')):
            writer.writerow([month, counts[month]])


def sorted_months(counts):
    """Return count keys ordered from earliest to latest month."""
    return sorted(counts, key=lambda value: datetime.strptime(value, '%Y/%m/%d'))


def write_creation_chart(output_file, counts, title, period_months=None):
    """Render a monthly-creation bar chart with a dotted median line."""
    import matplotlib

    matplotlib.use('Agg')
    from matplotlib import pyplot

    months = sorted_months(counts)
    if period_months is not None:
        months = months[-period_months:]
    creations = [counts[month] for month in months]

    figure, axis = pyplot.subplots(figsize=(max(10, len(months) * 0.45), 6))
    positions = range(len(months))
    axis.bar(positions, creations, color='#005ea8')
    if creations:
        median_creations = median(creations)
        axis.axhline(
            median_creations,
            color='#d54309',
            linestyle=':',
            linewidth=2,
            label=f'Median: {median_creations:g}',
        )
        axis.legend()
    else:
        axis.text(0.5, 0.5, 'No sandbox creations', ha='center', va='center')
    axis.set_title(title)
    axis.set_xlabel('Creation month')
    axis.set_ylabel('Sandbox creations')
    axis.set_xticks(list(positions), months, rotation=45, ha='right')
    axis.set_ylim(bottom=0)
    figure.tight_layout()
    figure.savefig(output_file, dpi=150)
    pyplot.close(figure)


def write_creation_charts(output_directory, report_name, counts):
    """Write all-time and trailing-24-month charts for one creation report."""
    report_title = report_name.replace('-', ' ').title()
    for period_name, period_months in CHART_PERIODS.items():
        period_title = 'All Time' if period_months is None else 'Last 24 Months'
        write_creation_chart(
            output_directory / f'{report_name}-{period_name}.png',
            counts,
            f'{report_title}: Creations by Month ({period_title})',
            period_months,
        )


def analyze(input_path):
    """Write all-sandbox and non-GSA monthly creation reports beside input."""
    input_file = Path(input_path)
    if not input_file.is_file():
        raise ValueError(f'Input CSV does not exist or is not a file: {input_file}')

    all_counts = creation_counts(input_file)
    non_gsa_counts = creation_counts(input_file, exclude_gsa=True)
    write_creation_counts(input_file.parent / 'all-sandboxes.csv', all_counts)
    write_creation_counts(input_file.parent / 'non-gsa-sandboxes.csv', non_gsa_counts)
    write_creation_charts(input_file.parent, 'all-sandboxes', all_counts)
    write_creation_charts(input_file.parent, 'non-gsa-sandboxes', non_gsa_counts)


def main():
    args = get_args()
    if args.analyze:
        try:
            analyze(args.analyze)
        except (OSError, ValueError) as error:
            print(f'Error: {error}', file=sys.stderr)
            return 1
        return 0

    test_authenticated()

    orgs = get_sandbox_orgs()
    logging.info('found %d sandbox org(s)', len(orgs))

    writer = csv.writer(sys.stdout)
    writer.writerow(['Org-name', 'Space-name', 'Creation-date'])

    for space in get_spaces(list(orgs.keys())):
        org_guid = space['relationships']['organization']['data']['guid']
        org_name = orgs.get(org_guid, '')
        writer.writerow([org_name, space['name'], space['created_at']])


def get_args():
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '-a',
        '--analyze',
        metavar='INPUT.csv',
        help='write monthly creation summaries for a CSV emitted by this script',
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='log API requests to stderr',
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        stream=sys.stderr,
    )
    return args


if __name__ == '__main__':
    sys.exit(main() or 0)
