import csv
rows = list(csv.DictReader(open("data/toy_labels.csv")))
seen, out = set(), []
for r in rows:
    if r["text"] not in seen:
        seen.add(r["text"]); out.append(r)
with open("data/toy_labels.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["id", "text", "label"]); w.writeheader(); w.writerows(out)
print(f"kept {len(out)} rows")
