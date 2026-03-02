#!/usr/bin/env python3
"""Parse NMC raw questions and output JSON. Correct answers from source page yellow highlight - not in text."""
import re
import json

def parse_line(line):
    line = line.strip()
    if not line or not re.match(r'^\d{4}\.', line):
        return None
    # Split from right: D. then C. then B. then A.
    try:
        rest, opt_d = line.rsplit(' D. ', 1)
        rest, opt_c = rest.rsplit(' C. ', 1)
        rest, opt_b = rest.rsplit(' B. ', 1)
        rest, opt_a = rest.split(' A. ', 1)
    except ValueError:
        return None
    # rest is "1001. question text"
    m = re.match(r'^(\d{4})\.\s*(.*)$', rest.strip())
    if not m:
        return None
    num, question = m.group(1), m.group(2).strip()
    return {
        'number': int(num),
        'question_text': question,
        'option_a': opt_a.strip(),
        'option_b': opt_b.strip(),
        'option_c': opt_c.strip(),
        'option_d': opt_d.strip(),
        'correct_answer': '',  # From yellow bg on source - fill manually or from live page
    }

def main():
    with open('nmc_1001_1100_raw.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        rec = parse_line(line)
        if rec:
            out.append(rec)
    with open('nmc_1001_1100.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f'Parsed {len(out)} questions -> nmc_1001_1100.json')

if __name__ == '__main__':
    main()
