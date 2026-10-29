Add an option to the script, -a or --analyze, that takes as input the CSV file
created by the script.

The analysis will output

- all-sandboxes.csv
- non-gsa-sandboxes.csv

with the columns:

- month/year
- creations

The creations will count the number of new sandboxes created during the month.
e.g.

```
2024/10/1, 17
2024/11/1, 24
```

The non-gsa-sandbox.csv will not count creations in the `sandbox-gsa` org.

Also make a plan for creating bar charts of creation by month for:
- all time
- the last 24 months

Each chart will have a horizontal dotted line for the median number
of sandboxes created per month during the period in question.

## Bar chart implementation plan

1. Use `all-sandboxes.csv` as the data source, retaining only its
   `month/year` and `creations` columns.
2. Produce an all-time chart from every row and a last-24-months chart from
   the most recent 24 rows. If fewer than 24 months are available, chart all
   available rows and label the period accordingly.
3. For each selected period, calculate the median of the plotted `creations`
   values (including zero-valued months only if they are represented in the
   input data) and draw a labeled horizontal dotted line at that value.
4. Render bars chronologically with readable monthly labels, a title naming
   the period, and axis labels for creation month and sandbox creations.
5. Save the charts next to the source CSV with these names:
   - `all-sandboxes-all-time.png`
   - `non-gsa-sandboxes-all-time.png`
   - `all-sandboxes-last-24-months.png`
   - `non-gsa-sandboxes-last-24-months.png`

The implementation uses the pinned `matplotlib` dependency in
`requirements.txt` and has chart-generation tests with a fixed fixture.
