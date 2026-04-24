import re
from collections import defaultdict
from spellchecker import SpellChecker

spell = SpellChecker(language='ro')

def read_md(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# ---------------------------
# 1. SPELL CHECK
# ---------------------------
def spell_check(text):
    words = re.findall(r'\b[a-zA-ZăâîșțĂÂÎȘȚ]+\b', text)
    unknown = spell.unknown(words)

    corrections = {}
    for word in unknown:
        corrections[word] = spell.correction(word)

    return corrections


# ---------------------------
# 2. EXTRACT TABLES (ASCII)
# ---------------------------
def extract_tables(text):
    tables = []
    current = []

    for line in text.splitlines():
        if "|" in line:
            current.append(line)
        else:
            if current:
                tables.append(current)
                current = []
    if current:
        tables.append(current)

    return tables


# ---------------------------
# 3. VALIDATE TABLE STRUCTURE
# ---------------------------
def validate_tables(tables):
    errors = []

    for idx, table in enumerate(tables):
        col_counts = []

        for row in table:
            cols = row.count("|")
            col_counts.append(cols)

        if len(set(col_counts)) > 1:
            errors.append(f"Tabel {idx}: număr inconsistent de coloane -> {col_counts}")

    return errors


# ---------------------------
# 4. EXTRACT NUMBERS
# ---------------------------
def extract_numbers(text):
    return list(map(int, re.findall(r'\b\d+\b', text)))


# ---------------------------
# 5. CHECK HOURS CONSISTENCY
# ---------------------------
def check_hours(text):
    issues = []

    # exemplu: verificăm dacă 42 + 28 = 70
    match = re.search(r'3\.4.?(\d+).?3\.5.?(\d+).?3\.6.*?(\d+)', text, re.S)
    if match:
        total, curs, lab = map(int, match.groups())
        if curs + lab != total:
            issues.append(f"Inconsistență ore: {curs} + {lab} != {total}")

    return issues


# ---------------------------
# 6. SIMPLE MATH CHECK
# ---------------------------
def check_simple_math(text):
    issues = []

    # caută expresii simple gen 5+3=9
    expressions = re.findall(r'(\d+)\s*([\+\-\\/])\s(\d+)\s*=\s*(\d+)', text)

    for a, op, b, result in expressions:
        a, b, result = int(a), int(b), int(result)

        if op == "+" and a + b != result:
            issues.append(f"{a}+{b}!={result}")
        elif op == "-" and a - b != result:
            issues.append(f"{a}-{b}!={result}")
        elif op == "*" and a * b != result:
            issues.append(f"{a}*{b}!={result}")
        elif op == "/" and b != 0 and a / b != result:
            issues.append(f"{a}/{b}!={result}")

    return issues


# ---------------------------
# MAIN
# ---------------------------
def analyze_md(file_path):
    text = read_md(file_path)

    print("=== SPELL CHECK ===")
    corrections = spell_check(text)
    for w, c in list(corrections.items())[:20]:
        print(f"{w} -> {c}")

    print("\n=== TABLE CHECK ===")
    tables = extract_tables(text)
    table_errors = validate_tables(tables)
    for err in table_errors:
        print(err)

    print("\n=== HOURS CHECK ===")
    for issue in check_hours(text):
        print(issue)

    print("\n=== MATH CHECK ===")
    for issue in check_simple_math(text):
        print(issue)


if _name_ == "_main_":
    analyze_md("fisier.md")