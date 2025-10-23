import argparse, json, os, sys, time, subprocess
from core.bus import MessageBus
from core.memory import Memory
from core.skills import SkillRegistry
from agents.planner import PlannerAgent
from agents.worker import WorkerAgent

DATA_DIR = "data"
STATE_FILE = os.path.join(DATA_DIR, "state.json")
LOG_FILE = os.path.join(DATA_DIR, "task_log.jsonl")

def ensure_dirs():
    for d in ["core","agents","runtime","skills","assets","data","scripts"]:
        os.makedirs(d, exist_ok=True)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    return {"projects": {}, "current_project":"default"}

def save_state(state):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE,"w",encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def log_task(event):
    with open(LOG_FILE,"a",encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def maybe_autobackup(do_backup: bool):
    if not do_backup:
        return
    try:
        # HANDOFF first
        subprocess.run([sys.executable, os.path.join("scripts","export_handoff.py")], check=False)
        # then ZIP
        subprocess.run([sys.executable, os.path.join("scripts","backup.py")], check=False)
        print("Auto-backup complete (handoff + zip).")
    except Exception as e:
        print("Auto-backup failed:", e)

def main():
    ensure_dirs()
    parser = argparse.ArgumentParser(description="Eclipsera runner")
    parser.add_argument("--goal", type=str, default="Create a small top-down demo",
                        help="High-level creation goal")
    parser.add_argument("--project", type=str, default="default", help="Project name")
    parser.add_argument("--viewer", action="store_true", help="Launch the viewer after generation")
    parser.add_argument("--autobackup", action="store_true", help="Export HANDOFF and create backup.zip after run")
    args = parser.parse_args()

    state = load_state()
    state["current_project"] = args.project
    if args.project not in state["projects"]:
        state["projects"][args.project] = {"created": time.time(), "notes": ""}

    bus = MessageBus()
    mem = Memory(os.path.join("data", f"{args.project}_memory.json"))
    skills = SkillRegistry(); skills.register_defaults()
    planner = PlannerAgent(bus, mem, skills, project=args.project)
    worker  = WorkerAgent(bus, mem, skills, project=args.project)

    plan = planner.propose_plan(args.goal)
    log_task({"ts": time.time(), "type":"plan", "plan": plan})
    for task in plan.get("tasks", []):
        result = worker.execute_task(task)
        log_task({"ts": time.time(), "type":"task_result", "task": task, "result": result})
        state["projects"][args.project].setdefault("artifacts", []).append(result)

    save_state(state)
    print("Generation done. See data/task_log.jsonl and assets/.")

    if args.viewer:
        from runtime.viewer import run_viewer
        run_viewer(args.project)

    maybe_autobackup(args.autobackup)
    print("Tip: manual handoff -> python scripts/export_handoff.py | manual backup -> python scripts/backup.py")

if __name__ == "__main__":
    main()
