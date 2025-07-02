import csv

# Read from the CSV file
unique_programs = set()

with open('EPA.csv', 'r') as csv_file:
    # Use csv.DictReader to parse the CSV
    csv_reader = csv.DictReader(csv_file)
    
    # Collect unique EPA programs
    for row in csv_reader:
        unique_programs.add(row['EPA program'])
    
    # Print the unique EPA programs
    print("Unique EPA Programs:")
    for program in sorted(unique_programs):
        print(program)
