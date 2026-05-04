import json
from collections import defaultdict
import os

data = json.load(open("repository/NVDA.json"))
down_days = [x for x in data if float(x["change2"].replace("%", "")) < -50.0]

yearly_count = defaultdict(int)
for d in down_days:
    year = d["date"][:4]
    yearly_count[year] += 1

scratch_file = "/Users/yulinchen/.gemini/antigravity/brain/ef7a9dbb-8cac-47eb-a996-8e1f1e0d2e97/scratch/nvda_50_percent_drops.txt"
with open(scratch_file, "w") as f:
    f.write("Full list of trading days where NVDA was down >50% from its ATH:\n")
    f.write("-" * 60 + "\n")
    for d in down_days:
        f.write(f"{d['date']}: {d['change2']}\n")

print("| Year | Days >50% Down |")
print("|------|----------------|")
for year in sorted(yearly_count.keys()):
    print(f"| {year} | {yearly_count[year]} |")

