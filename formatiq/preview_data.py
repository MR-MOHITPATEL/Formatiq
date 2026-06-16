import csv
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scraped_videos.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total videos: {len(rows)}")
print()
print(f"{'Title':<60} {'Channel':<30} {'Views':>10}  {'Format Point'}")
print("-" * 120)
for r in rows[:20]:
    title = r.get('title', '')[:58]
    ch = r.get('channel_name', '')[:28]
    views = r.get('view_count', '0')
    fp = r.get('format_point', '')[:25]
    print(f"{title:<60} {ch:<30} {views:>10}  {fp}")

print()
print("--- Top 10 by views ---")
rows_sorted = sorted(rows, key=lambda x: int(x.get('view_count', 0) or 0), reverse=True)
for r in rows_sorted[:10]:
    title = r.get('title', '')[:58]
    views = int(r.get('view_count', 0) or 0)
    fp = r.get('format_point', '')[:25]
    print(f"{views:>12,}  {title:<60}  [{fp}]")

print()
print("--- Videos with transcripts ---")
with_transcript = sum(1 for r in rows if r.get('transcript_available') == 'True')
print(f"{with_transcript}/{len(rows)} videos have transcripts available")

print()
print("--- Count per format point ---")
from collections import Counter
fp_counts = Counter(r.get('format_point', '') for r in rows)
for fp, count in sorted(fp_counts.items()):
    print(f"  {count:>4}  {fp}")
