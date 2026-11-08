import csv
rows = list(csv.DictReader(open("data/toy_labels.csv")))
print(f"loaded {len(rows)} rows")
