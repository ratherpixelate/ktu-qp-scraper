import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter

DOWNLOADS_DIR = Path(__file__).parent / "downloads"
OUTPUT_DIR = Path(__file__).parent / "papers"

COURSE_CODE_RE = re.compile(r"Course Code:\s*([^\n]+)")
SEMESTER_NUM_RE = re.compile(r"(\d+)")


def extract_course_code(text: str) -> str | None:
    m = COURSE_CODE_RE.search(text)
    if not m:
        return None
    # PDF text extraction sometimes inserts stray spaces inside a course
    # code (e.g. "PBCVT 404" instead of "PBCVT404") due to font kerning —
    # capture the whole line and strip internal whitespace back out.
    code = re.sub(r"\s+", "", m.group(1))
    return code or None


def split_bundle(pdf_path: Path, semester_num: str, branch_name: str) -> None:
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    page_codes = [extract_course_code(t) for t in page_texts]

    # A page with a "Course Code:" line is the start of a new subject —
    # layout-order-independent, unlike checking the literal first line for
    # "MODEL QUESTION PAPER" (some archived/scanned PDFs extract text in a
    # different line order, which made that check miss real boundaries).
    boundaries = [i for i, code in enumerate(page_codes) if code]

    if not boundaries:
        print(f"  [warn] no subject boundaries found in {pdf_path.name}, skipping")
        return

    if boundaries[0] != 0:
        print(f"  [warn] {pdf_path.name}: {boundaries[0]} leading page(s) before first "
              f"subject boundary — discarding them")

    seen_codes: dict[str, int] = {}  # subject_code -> first start page, for dup detection

    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(reader.pages)
        subject_code = page_codes[start]

        if subject_code in seen_codes:
            print(f"  [warn] {subject_code} appears again at pages {start}-{end - 1} "
                  f"(first seen at page {seen_codes[subject_code]}) — keeping first occurrence, skipping this one")
            continue
        seen_codes[subject_code] = start

        writer = PdfWriter()
        for p in range(start, end):
            writer.add_page(reader.pages[p])

        out_dir = OUTPUT_DIR / semester_num / branch_name / subject_code
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{subject_code} (MOD).pdf"

        with open(out_path, "wb") as f:
            writer.write(f)
        print(f"  [saved] {out_path}")


def main():
    if not DOWNLOADS_DIR.exists():
        raise SystemExit(f"{DOWNLOADS_DIR} does not exist — run fetch_qps.py first")

    for semester_dir in sorted(DOWNLOADS_DIR.iterdir()):
        if not semester_dir.is_dir():
            continue

        m = SEMESTER_NUM_RE.search(semester_dir.name)
        if not m:
            print(f"[warn] could not parse semester number from '{semester_dir.name}', skipping")
            continue
        semester_num = m.group(1)

        for pdf_path in sorted(semester_dir.glob("*.pdf")):
            branch_name = pdf_path.stem  # e.g. "GROUP A" or "COMPUTER SCIENCE AND ENGINEERING"
            print(f"\n[{semester_dir.name}] {branch_name}")
            split_bundle(pdf_path, semester_num, branch_name)

    print("\nFinished splitting all bundles :]")


if __name__ == "__main__":
    main()