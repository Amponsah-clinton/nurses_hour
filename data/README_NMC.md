# NMC Past Questions (1001–1100) — Data

Source: [1001–1100 Solved NMC Licensure Past Question Bank](https://www.tellitnurse.com/2025/05/1001-1300-nmc-past-question-bank.html) (tellitnurse.com).

## Files

| File | Description |
|------|-------------|
| **nmc_1001_1100.json** | All 100 questions with `question_text`, `option_a`–`option_d`, and **correct_answer** (A/B/C/D) extracted from the source page (yellow-highlighted option = `<mark>` in HTML). |
| **NMC_1001_1100_QUESTIONS_AND_ANSWERS.md** | Human-readable list of every question, options A–D, and the correct answer. |
| **nmc_1001_1100_raw.txt** | Raw one-line-per-question text used for parsing. |
| **parse_nmc.py** | Parses the raw text into JSON (question + options). |
| **fetch_answers.py** | Fetches the tellitnurse HTML and extracts correct answers from `<mark>`-wrapped options, then updates the JSON. |
| **generate_readme.py** | Builds `NMC_1001_1100_QUESTIONS_AND_ANSWERS.md` from the JSON. |

## How answers were obtained

On the source page, the correct option for each question is shown with a **yellow background**. In the HTML that is implemented with a `<mark>` tag (e.g. `D. <mark>I, II, III and IV</mark>`). The script `fetch_answers.py` downloads the page and sets `correct_answer` in the JSON to the letter (A, B, C, or D) whose option text is inside `<mark>`.

## Using the JSON in your app

You can import `nmc_1001_1100.json` into your Django/Supabase MCQ bank. Each object has:

- `number` (1001–1100)
- `question_text`
- `option_a`, `option_b`, `option_c`, `option_d`
- `correct_answer` (`"A"`, `"B"`, `"C"`, or `"D"`)

Optionally run a management command or script that reads the JSON and creates `MCQQuestion` records (and syncs to Supabase if needed).
