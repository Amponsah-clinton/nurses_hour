#!/usr/bin/env python3
"""Generate NMC_1001_1100_QUESTIONS_AND_ANSWERS.md from JSON."""
import json

with open('nmc_1001_1100.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

lines = [
    '# NMC Past Question Bank — Questions 1001–1100',
    '',
    'Source: [1001–1100 Solved NMC Licensure Past Question Bank](https://www.tellitnurse.com/2025/05/1001-1300-nmc-past-question-bank.html)',
    '',
    '**On the source page, the correct answer is the option with the yellow background (marked with `<mark>` in HTML).**',
    'Answers below were extracted from the source page.',
    '',
    '---',
    ''
]

for q in data:
    num = q['number']
    lines.append(f'## {num}')
    lines.append('')
    lines.append(q['question_text'])
    lines.append('')
    lines.append(f"- **A.** {q['option_a']}")
    lines.append(f"- **B.** {q['option_b']}")
    lines.append(f"- **C.** {q['option_c']}")
    lines.append(f"- **D.** {q['option_d']}")
    lines.append('')
    ans = q.get('correct_answer') or '_'
    lines.append(f'**Answer:** {ans}')
    lines.append('')
    lines.append('---')
    lines.append('')

with open('NMC_1001_1100_QUESTIONS_AND_ANSWERS.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('Generated NMC_1001_1100_QUESTIONS_AND_ANSWERS.md')
