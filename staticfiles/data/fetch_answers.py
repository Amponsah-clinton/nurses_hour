#!/usr/bin/env python3
"""Fetch tellitnurse page HTML and extract correct answers (marked with <mark>)."""
import urllib.request
import re
import json

req = urllib.request.Request(
    'https://www.tellitnurse.com/2025/05/1001-1300-nmc-past-question-bank.html',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'}
)
with urllib.request.urlopen(req, timeout=20) as r:
    html = r.read().decode('utf-8', errors='replace')

# Post content
start = html.find("id='post-body'")
if start == -1:
    start = html.find('post-body')
body_start = html.find('>', start) + 1
body = html[body_start:body_start+800000]
# Split by </div><br or </div> followed by <div> to get each question block
parts = re.split(r'</div>\s*(?:<br\s*/?>\s*)?', body)
answers = {}  # number -> 'A'|'B'|'C'|'D'

for block in parts:
    # Question block may start with "1001. " or "<div>1001. "
    m = re.search(r'(\d{4})\.', block)
    if not m:
        continue
    num = int(m.group(1))
    if num < 1001 or num > 1100:
        continue
    # Which option has <mark>? "D. <mark>..." -> answer D
    for letter in ['D', 'C', 'B', 'A']:
        if re.search(re.escape(letter) + r'\.\s*<mark>', block):
            answers[num] = letter
            break

print(f'Extracted {len(answers)} answers (1001-1100)')

# Load JSON and update correct_answer
with open('nmc_1001_1100.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for q in data:
    num = q['number']
    if num in answers:
        q['correct_answer'] = answers[num]

with open('nmc_1001_1100.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print('Updated nmc_1001_1100.json with correct answers')
# Show first 5
for q in data[:5]:
    print(f"  {q['number']}: {q['correct_answer']}")
