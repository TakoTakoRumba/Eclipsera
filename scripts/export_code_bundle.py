# scripts/export_code_bundle.py
import os, datetime, pathlib

EXCLUDE_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".idea", ".vscode"}
EXCLUDE_EXTS = {".zip", ".pyc"}

def should_skip(path: pathlib.Path):
    parts = set(path.parts)
    if parts & EXCLUDE_DIRS:
        return True
    if path.suffix.lower() in EXCLUDE_EXTS:
        return True
    return False

def file_tree(root="."):
    lines=[]
    base = pathlib.Path(root).resolve()
    for p in sorted(base.rglob("*")):
        if p.is_dir():
            rel = p.relative_to(base)
            if should_skip(p): continue
            lines.append(str(rel) + "/")
        else:
            rel = p.relative_to(base)
            if should_skip(p): continue
            lines.append(str(rel))
    return "\n".join(lines)

def main():
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    base = pathlib.Path(".").resolve()
    outdir = base / "data"
    outdir.mkdir(exist_ok=True)
    out = outdir / "CODEBUNDLE.txt"

    with out.open("w", encoding="utf-8") as f:
        f.write(f"ECLIPSERA CODE BUNDLE — {ts}\n")
        f.write("Format: Each file is delimited by lines starting with === FILE: and === END FILE ===\n\n")

        # include file tree for readability
        f.write("FILE TREE\n---------\n")
        f.write(file_tree("."))
        f.write("\n\n")

        for p in sorted(base.rglob("*")):
            if p.is_dir(): 
                continue
            if should_skip(p): 
                continue
            rel = p.relative_to(base)
            try:
                content = p.read_text(encoding="utf-8")
            except Exception:
                # skip binary files just in case
                continue
            f.write(f"=== FILE: {rel.as_posix()} ===\n")
            f.write(content)
            f.write("\n=== END FILE ===\n\n")

    print(f"✅ Wrote {out}")

if __name__ == "__main__":
    main()
