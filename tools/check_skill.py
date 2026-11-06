"""Guard against silently losing detail from the value-investing skill.

Compares an OLD and a NEW SKILL.md and fails if the new one:
  - drops any number, dollar amount or quoted phrase that the old one had,
  - drops or renumbers any of the "## N." section headings, or
  - is smaller than the old one.

Usage: python tools/check_skill.py OLD_SKILL.md NEW_SKILL.md
"""
import re
import sys

NUM = r"[-−]?\$?\d+(?:[.,]\d+)*%?"
QUOTE = r'"[^"\n;]{8,150}"'


def norm(text):
    return text.replace("−", "-").replace(",", "")


def body(text):
    """Skip the header and the 'Last Updated' date, which change every time."""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    return re.sub(r"^\*\*Last Updated:\*\*.*$", "", text, flags=re.M)


def tokens(text):
    text = body(text)
    return set(re.findall(NUM, text)) | set(re.findall(QUOTE, text))


def reworded_quote(tok, new_norm):
    """A quote that was only reworded keeps every one of its words."""
    if not tok.startswith('"'):
        return False
    words = re.findall(r"[\w']{3,}", norm(tok).lower())
    return all(w in new_norm.lower() for w in words)


def headings(text):
    return re.findall(r"^## (\d+)\.", text, flags=re.M)


def main(old_path, new_path):
    old = open(old_path, encoding="utf-8").read()
    new = open(new_path, encoding="utf-8").read()
    problems = []

    new_norm = norm(new)
    lost = sorted(t for t in tokens(old) if norm(t) not in new_norm and not reworded_quote(t, new_norm))
    if lost:
        problems.append("Numbers or quotes removed: " + ", ".join(lost))

    if headings(old) != headings(new)[: len(headings(old))]:
        problems.append(f"Section headings changed: {headings(old)} -> {headings(new)}")

    if len(new.encode()) < len(old.encode()):
        problems.append(f"File got smaller: {len(old.encode())} -> {len(new.encode())} bytes")

    if problems:
        print("SKILL CHECK FAILED: detail may have been lost.")
        for p in problems:
            print(" - " + p)
        print("If a removal is intended, Chris must approve it first.")
        return 1
    print(f"SKILL CHECK PASSED: nothing removed ({len(tokens(old))} numbers/quotes kept, sections intact).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
