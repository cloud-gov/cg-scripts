import csv
from collections import defaultdict

program_spaces = defaultdict(set)

with open('EPA.csv', 'r') as csv_file:
    # Use csv.DictReader to parse the CSV
    csv_reader = csv.DictReader(csv_file)
    
    # Collect unique EPA programs
    for row in csv_reader:
        program = row['EPA Program']
        space = row['EPA Space']
        program_spaces[program].add(space)

    
# Print the unique EPA programs
for program in sorted(program_spaces.keys()):
    spaces = " ".join(list(program_spaces[program]))
    org = program.split('--')[0]
    if (spaces =='*'):
        print(f"./estimate-costs {org} -a {program}")
    else:
        print(f"./estimate-costs {org} -a {program} -s {spaces}")
