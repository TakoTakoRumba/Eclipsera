# scripts/export_handoff.py
import os, json, datetime, textwrap

ROOT = "."

def read_json_lines(path):
    if not os.path.exists(path): return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out

def file_tree(root="."):
    lines=[]
    base_depth = root.count(os.sep)
    for r, dirs, files in os.walk(root):
        # prune noisy stuff
        dirs[:] = [d for d in dirs if d not in (".venv","__pycache__", ".git", "node_modules")]
        depth = r.count(os.sep)-base_depth
        indent = "  "*depth
        name = os.path.basename(r) or r
        lines.append(f"{indent}{name}")
        for f in sorted(files):
            if f.endswith((".zip",".pyc")): continue
            lines.append(f"{indent}  - {f}")
    return "\n".join(lines)

def last_plan_summary(task_log_events):
    # find the last event of type "plan"
    for ev in reversed(task_log_events):
        if ev.get("type") == "plan":
            plan = ev.get("plan", {})
            goal = plan.get("goal", "(unknown)")
            tasks = plan.get("tasks", [])
            tasks_str = "\n".join([f"  - {t.get('skill')} {t.get('args',{})}" for t in tasks])
            return f"Goal: {goal}\nTasks:\n{tasks_str}"
    return "No plan recorded yet."

def main():
    now = datetime.datetime.now().isoformat(timespec="seconds")
    os.makedirs("data", exist_ok=True)

    state = {}
    if os.path.exists("data/state.json"):
        try:
            with open("data/state.json","r",encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass

    events = read_json_lines("data/task_log.jsonl")
    plan_str = last_plan_summary(events)

    outlines = [p for p in os.listdir("data") if p.endswith("_outline.json")]
    projects = list(state.get("projects", {}).keys())

    handoff = f"""ECLIPSERA HANDOFF — {now}

What this is
------------
Autonomous agents that generate a small playable slice (outline, level JSON, NPCs, dialogue) plus a simple viewer.

How to run on a fresh machine (Windows, PowerShell)
---------------------------------------------------
1) Create/activate venv:
   py -m venv .venv
   . .\\.venv\\Scripts\\Activate.ps1
   python -m pip install --upgrade pip setuptools wheel
2) Install viewer dependency:
   pip install pygame-ce
3) Generate & run viewer:
   python run.py --goal "Create a small top-down demo with coins and two NPCs" --project default --viewer

Current project snapshot
------------------------
Projects in state: {projects}
Outlines found: {outlines}
Task log present: {bool(events)}

Last recorded plan
------------------
{plan_str}

File tree
---------
{file_tree(ROOT)}

Next suggested steps
--------------------
- Add collisions & dialogue UI to the viewer.
- Add richer NPC generation (traits, movement patterns).
- Add Critic agent to propose v2/v3 refinements.
"""

    out_path = "data/HANDOFF.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(handoff)

    print("✅ Created:", out_path)
    print("Seemless Thread.")

if __name__ == "__main__":
    main()
