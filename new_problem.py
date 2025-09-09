import os
import sys
from pathlib import Path
import re

TEMPLATE_FILE = "template.py"
README_FILE = "README.md"
PROGRESS_START = "<!-- PROGRESS:START -->"
PROGRESS_END = "<!-- PROGRESS:END -->"

BASE_DIR = Path(__file__).parent

def slugify(name: str) -> str:
    return (
        name.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("'", "")
    )

def load_template():
    path = BASE_DIR / TEMPLATE_FILE
    if not path.exists():
        print(f"Error: {TEMPLATE_FILE} not found.")
        sys.exit(1)
    return path.read_text(encoding="utf-8")

def ensure_readme():
    readme_path = BASE_DIR / README_FILE
    if not readme_path.exists():
        # Minimal default
        readme_path.write_text(
            "# NeetCode 150 – My Progress\n\n"
            "Goal: 5 problems/week\n\n"
            "## Progress Summary\n- Total: 0 done / 150 planned\n\n"
            "---\n\n"
            f"{PROGRESS_START}\n"
            "## Arrays\n(none yet)\n\n"
            "## Two Pointers\n(none yet)\n\n"
            "## Sliding Window\n(none yet)\n\n"
            "## Stack\n(none yet)\n\n"
            "## Binary Search\n(none yet)\n\n"
            f"{PROGRESS_END}\n",
            encoding="utf-8",
        )
    return readme_path.read_text(encoding="utf-8")

def write_readme(content: str):
    (BASE_DIR / README_FILE).write_text(content, encoding="utf-8")

def upsert_category_block(progress_block: str, category_title: str) -> str:
    """
    Ensure a '## {category_title}' section exists in the progress block.
    Return updated progress block.
    """
    pattern = rf"(?m)^## {re.escape(category_title)}\s*(.+?)(?=^## |\Z)"
    if re.search(pattern, progress_block, flags=re.DOTALL):
        return progress_block  # already exists
    # Append a new empty section before PROGRESS_END
    return progress_block.rstrip() + f"\n\n## {category_title}\n(none yet)\n\n"

def add_problem_checkbox(progress_block: str, category_title: str, problem_name: str, link: str, path_str: str, done: bool) -> str:
    """
    Insert a checkbox line under the category. Avoid duplicates.
    """
    pattern = rf"(?ms)(^## {re.escape(category_title)}\s*)(.+?)(?=^## |\Z)"
    match = re.search(pattern, progress_block)
    if not match:
        # category missing (should not happen if we called upsert_category_block)
        progress_block = upsert_category_block(progress_block, category_title)
        match = re.search(pattern, progress_block)

    section_start, section_body = match.group(1), match.group(2)

    checkbox = "[x]" if done else "[ ]"
    line = f"- {checkbox} [{problem_name}]({link}) — `{path_str}`"

    # If "(none yet)" exists, replace it outright
    if "(none yet)" in section_body:
        new_body = section_body.replace("(none yet)", line)
    else:
        # Avoid duplicates by checking problem name
        if re.search(re.escape(f"[{problem_name}]("), section_body):
            # Already present: optionally upgrade to done
            if done:
                # turn the matching line into [x]
                section_body = re.sub(
                    rf"(?m)^- \[ \] \[{re.escape(problem_name)}\]\([^)]+\) — `[^`]+`$",
                    lambda m: m.group(0).replace("[ ]", "[x]"),
                    section_body,
                )
            new_body = section_body
        else:
            # Append at end of section
            new_body = section_body.rstrip() + "\n" + line + "\n"

    # Put section back
    start_idx, end_idx = match.span()
    updated = progress_block[:start_idx] + section_start + new_body + progress_block[end_idx:]
    return updated

def update_summary_counts(readme: str) -> str:
    """
    Recompute 'Total: X done / 150 planned' in the Summary section.
    """
    # Count done/total inside PROGRESS block
    progress = extract_progress_block(readme)
    total = len(re.findall(r"(?m)^- \[(?: |x)\]", progress))
    done = len(re.findall(r"(?m)^- \[x\]", progress))

    readme = re.sub(
        r"(?m)^(## Progress Summary\s*\n- Total: )\d+ done / \d+ planned$",
        rf"\g<1>{done} done / 150 planned",
        readme,
    )
    return readme

def extract_progress_block(readme: str) -> str:
    pattern = rf"{re.escape(PROGRESS_START)}(.*?){re.escape(PROGRESS_END)}"
    m = re.search(pattern, readme, flags=re.DOTALL)
    if not m:
        # If the markers are missing, create them with a default block
        default = f"{PROGRESS_START}\n## Arrays\n(none yet)\n\n{PROGRESS_END}"
        return default
    return m.group(1)

def replace_progress_block(readme: str, new_block: str) -> str:
    pattern = rf"{re.escape(PROGRESS_START)}(.*?){re.escape(PROGRESS_END)}"
    if re.search(pattern, readme, flags=re.DOTALL):
        return re.sub(pattern, f"{PROGRESS_START}{new_block}{PROGRESS_END}", readme, flags=re.DOTALL)
    else:
        # If markers missing, append
        return readme.rstrip() + "\n\n" + PROGRESS_START + new_block + PROGRESS_END + "\n"

def main():
    if len(sys.argv) < 4:
        print("Usage: python new_problem.py \"Problem Name\" \"https://link\" category [--done]")
        sys.exit(1)

    problem_name = sys.argv[1]
    problem_link = sys.argv[2]
    category = sys.argv[3]
    mark_done = ("--done" in sys.argv)

    # 1) Create code file from template
    template = load_template()
    filled = (
        template
        .replace("PROBLEM_NAME", problem_name)
        .replace("PROBLEM_LINK", problem_link)
        .replace("CATEGORY", category.replace('_', ' ').title())
        .replace("DIFFICULTY", "TBD")
    )

    category_dir = BASE_DIR / category
    category_dir.mkdir(exist_ok=True)
    filename = slugify(problem_name) + ".py"
    output_path = category_dir / filename

    if output_path.exists():
        print(f"Note: {output_path} already exists (won't overwrite).")
    else:
        output_path.write_text(filled, encoding="utf-8")
        print(f"Created: {output_path}")

    # 2) Update README progress block
    readme = ensure_readme()
    progress_block = extract_progress_block(readme)

    # Make sure category header exists
    category_title = category.replace('_', ' ').title()
    progress_block = upsert_category_block(progress_block, category_title)

    # Add (or mark) the problem line
    path_str = f"{category}/{filename}"
    progress_block = add_problem_checkbox(
        progress_block, category_title, problem_name, problem_link, path_str, mark_done
    )

    # 3) Put progress block back & update summary counts
    new_readme = replace_progress_block(readme, progress_block)
    new_readme = update_summary_counts(new_readme)
    write_readme(new_readme)

    print(f"Updated README with '{problem_name}' under '{category_title}' (done={mark_done}).")

if __name__ == "__main__":
    main()
