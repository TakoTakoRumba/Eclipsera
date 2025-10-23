import os, json, textwrap, zipfile, datetime, shutil

ROOT = os.getcwd()

FILES = {
    "README.md": """# Eclipsera
Autonomous agents that create video games (content, levels, NPCs, and runtime).
- Run: `python run.py`
- Export handoff: `python scripts\\export_handoff.py`
- Backup zip: `python scripts\\backup.py`
""",

    "run.py": """import argparse, json, os, sys, time
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
        f.write(json.dumps(event, ensure_ascii=False) + "\\n")

def main():
    ensure_dirs()
    parser = argparse.ArgumentParser(description="Eclipsera runner")
    parser.add_argument("--goal", type=str, default="Create a small top-down demo",
                        help="High-level creation goal")
    parser.add_argument("--project", type=str, default="default", help="Project name")
    parser.add_argument("--viewer", action="store_true", help="Launch the viewer after generation")
    args = parser.parse_args()

    state = load_state()
    state["current_project"] = args.project
    if args.project not in state["projects"]:
        state["projects"][args.project] = {"created": time.time(), "notes": ""}

    bus = MessageBus()
    mem = Memory(os.path.join("data", f"{args.project}_memory.json"))
    skills = SkillRegistry()
    skills.register_defaults()

    planner = PlannerAgent(bus, mem, skills, project=args.project)
    worker  = WorkerAgent(bus, mem, skills, project=args.project)

    plan = planner.propose_plan(args.goal)
    log_task({"ts": time.time(), "type":"plan", "plan": plan})
    for task in plan.get("tasks", []):
        result = worker.execute_task(task)
        log_task({"ts": time.time(), "type":"task_result", "task": task, "result": result})
        state["projects"][args.project].setdefault("artifacts", []).append(result)

    save_state(state)

    if args.viewer:
        from runtime.viewer import run_viewer
        run_viewer(args.project)

    print("Done. See data/task_log.jsonl and assets/ for outputs.")
    print("Tip: export handoff -> python scripts/export_handoff.py")

if __name__ == "__main__":
    main()
""",

    os.path.join("core","bus.py"): """class MessageBus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, topic, fn):
        self._subscribers.setdefault(topic, []).append(fn)

    def publish(self, topic, payload):
        for fn in self._subscribers.get(topic, []):
            fn(payload)
""",

    os.path.join("core","memory.py"): """import json, os

class Memory:
    def __init__(self, path):
        self.path = path
        self.data = {"notes": [], "facts": []}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                pass

    def add_note(self, text):
        self.data["notes"].append(text)
        self._save()

    def remember(self, fact):
        self.data["facts"].append(fact)
        self._save()

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
""",

    os.path.join("core","skills.py"): """import json, os, time

class SkillRegistry:
    def __init__(self):
        self.skills = {}

    def register(self, name, fn):
        self.skills[name] = fn

    def call(self, name, **kwargs):
        if name not in self.skills:
            raise KeyError(f"Unknown skill: {name}")
        return self.skills[name](**kwargs)

    def register_defaults(self):
        self.register("design_game_outline", self._design_game_outline)
        self.register("generate_level_json", self._generate_level_json)
        self.register("generate_npcs", self._generate_npcs)
        self.register("write_dialogue", self._write_dialogue)

    def _design_game_outline(self, goal:str, project:str):
        ts = int(time.time())
        outline = {
            "project": project,
            "timestamp": ts,
            "pitch": f"A tiny vertical slice toward: {goal}",
            "mechanics": ["top-down movement", "collect items", "talk to NPCs"],
            "art": "placeholder sprites",
            "music": "placeholder loop",
            "levels": ["meadow_v1"],
            "npcs": ["guide_v1","merchant_v1"]
        }
        self._write_json(f"data/{project}_outline.json", outline)
        return {"type":"outline", "path": f"data/{project}_outline.json", "summary":"Game outline created."}

    def _generate_level_json(self, name:str, project:str):
        level = {
            "name": name,
            "tiles": [["." for _ in range(16)] for _ in range(12)],
            "player_spawn": [2,2],
            "objects": [{"type":"coin","x":5,"y":5},{"type":"sign","x":8,"y":3,"text":"Hello!"}]
        }
        p = f"assets/{project}_level_{name}.json"
        self._write_json(p, level)
        return {"type":"level", "path": p, "summary": f"Level {name} generated."}

    def _generate_npcs(self, project:str):
        npcs = [
            {"id":"guide_v1","name":"Astra","role":"guide","x":4,"y":4},
            {"id":"merchant_v1","name":"Roux","role":"merchant","x":9,"y":6}
        ]
        p = f"assets/{project}_npcs.json"
        self._write_json(p, npcs)
        return {"type":"npcs", "path": p, "summary": "Basic NPCs created."}

    def _write_dialogue(self, project:str):
        dlg = {
            "guide_v1":[
                {"who":"Astra","text":"Welcome to Eclipsera!"},
                {"who":"Astra","text":"Collect 5 coins and visit Roux."}
            ],
            "merchant_v1":[
                {"who":"Roux","text":"Care to trade a coin for a hint?"}
            ]
        }
        p = f"assets/{project}_dialogue.json"
        self._write_json(p, dlg)
        return {"type":"dialogue","path":p,"summary":"Dialogue written."}

    def _write_json(self, path, obj):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
""",

    os.path.join("agents","planner.py"): """class PlannerAgent:
    def __init__(self, bus, memory, skills, project:str):
        self.bus = bus
        self.memory = memory
        self.skills = skills
        self.project = project

    def propose_plan(self, goal:str):
        tasks = [
            {"skill":"design_game_outline","args":{"goal":goal, "project":self.project}},
            {"skill":"generate_level_json","args":{"name":"meadow_v1","project":self.project}},
            {"skill":"generate_npcs","args":{"project":self.project}},
            {"skill":"write_dialogue","args":{"project":self.project}}
        ]
        self.memory.add_note(f"Planned {len(tasks)} tasks toward: {goal}")
        return {"goal": goal, "tasks": tasks}
""",

    os.path.join("agents","worker.py"): """class WorkerAgent:
    def __init__(self, bus, memory, skills, project:str):
        self.bus = bus
        self.memory = memory
        self.skills = skills
        self.project = project

    def execute_task(self, task:dict):
        name = task.get("skill")
        args = task.get("args", {})
        result = self.skills.call(name, **args)
        self.memory.add_note(f"Executed {name}")
        return result
""",

    os.path.join("runtime","viewer.py"): """import json, os, sys, time
import pygame

def load_level(path):
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def load_npcs(path):
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def run_viewer(project:str):
    level_path = f"assets/{project}_level_meadow_v1.json"
    npcs_path  = f"assets/{project}_npcs.json"
    dialogue_path = f"assets/{project}_dialogue.json"

    if not (os.path.exists(level_path) and os.path.exists(npcs_path)):
        print("No generated assets yet. Run: python run.py --viewer")
        return

    with open(dialogue_path,"r",encoding="utf-8") as f:
        dialogue = json.load(f)

    lvl = load_level(level_path)
    npcs = load_npcs(npcs_path)

    pygame.init()
    tile = 32
    w, h = len(lvl["tiles"][0])*tile, len(lvl["tiles"])*tile
    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption("Eclipsera Viewer")

    clock = pygame.time.Clock()
    px, py = lvl["player_spawn"]
    player = pygame.Rect(px*tile, py*tile, tile, tile)
    speed = 3

    def draw():
        screen.fill((30,30,30))
        for y,row in enumerate(lvl["tiles"]):
            for x,_ in enumerate(row):
                pygame.draw.rect(screen,(60,60,60), pygame.Rect(x*tile,y*tile,tile,tile),1)
        for obj in lvl.get("objects",[]):
            r = pygame.Rect(obj["x"]*tile, obj["y"]*tile, tile, tile)
            pygame.draw.rect(screen,(200,200,0) if obj["type"]=="coin" else (0,150,200), r)
        for n in npcs:
            r = pygame.Rect(n["x"]*tile, n["y"]*tile, tile, tile)
            pygame.draw.rect(screen,(200,80,80), r)
        pygame.draw.rect(screen,(200,200,200), player)
        pygame.display.flip()

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); return
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += speed
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy -= speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy += speed
        player.move_ip(dx,dy)
        draw()
        clock.tick(60)
"""
}

def write_files():
    for path, content in FILES.items():
        full = os.path.join(ROOT, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(content))

def main():
    write_files()
    print("✅ Eclipsera scaffold created successfully.")
    print("Next steps:")
    print("1️⃣ Run your first generation:")
    print("   python run.py --goal \"Create a small top-down demo\" --project default --viewer")
    print("2️⃣ (Optional) Export handoff for new ChatGPT session:")
    print("   python scripts/export_handoff.py")
    print("3️⃣ (Optional) Backup:")
    print("   python scripts/backup.py")

if __name__ == "__main__":
    main()
