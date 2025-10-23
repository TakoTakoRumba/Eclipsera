# scripts/restore_from_bundle.py
import os, re, pathlib

BUNDLE_PATH = pathlib.Path("data/CODEBUNDLE.txt")

def main():
    if not BUNDLE_PATH.exists():
        print("ERROR: data/CODEBUNDLE.txt not found.")
        return
    text = BUNDLE_PATH.read_text(encoding="utf-8")
    # pattern to match sections
    pattern = re.compile(r"^=== FILE: (.+?) ===\n(.*?)\n=== END FILE ===", re.S | re.M)
    matches = pattern.findall(text)
    if not matches:
        print("No files found in bundle. Make sure the format matches export_code_bundle.py.")
        return

    for rel, content in matches:
        rel_path = pathlib.Path(rel)
        rel_path.parent.mkdir(parents=True, exist_ok=True)
        rel_path.write_text(content, encoding="utf-8")
        print("Wrote", rel)

    print("✅ Restore complete.")

if __name__ == "__main__":
    main()
