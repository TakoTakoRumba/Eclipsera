import json, os, time, random

class SkillRegistry:
    def __init__(self):
        self.skills = {}

    def register(self, name, fn):
        self.skills[name] = fn

    # NOTE: use skill_name to avoid clashing with task arg "name"
    def call(self, skill_name, **kwargs):
        if skill_name not in self.skills:
            raise KeyError(f"Unknown skill: {skill_name}")
        return self.skills[skill_name](**kwargs)

    def register_defaults(self):
        self.register("design_game_outline", self._design_game_outline)
        self.register("generate_level_json", self._generate_level_json)
        self.register("generate_npcs", self._generate_npcs)
        self.register("write_dialogue", self._write_dialogue)

    # --- Basic skills ---

    def _design_game_outline(self, goal:str, project:str):
        ts = int(time.time())
        outline = {
            "project": project,
            "timestamp": ts,
            "pitch": f"A tiny vertical slice toward: {goal}",
            "mechanics": ["top-down movement", "collision", "talk to NPCs (E)"],
            "art": "placeholder sprites",
            "music": "placeholder loop",
            "levels": ["meadow_v1"],
            "npcs": ["guide_v1","merchant_v1"]
        }
        self._write_json(f"data/{project}_outline.json", outline)
        return {"type":"outline", "path": f"data/{project}_outline.json", "summary":"Game outline created."}

    def _generate_level_json(self, name:str, project:str):
        import random
        W, H = 16, 12
        tiles = [["." for _ in range(W)] for _ in range(H)]

        # Solid border
        for x in range(W):
            tiles[0][x] = "#"; tiles[H-1][x] = "#"
        for y in range(H):
            tiles[y][0] = "#"; tiles[y][W-1] = "#"

        # Random interior walls
        random.seed(42)
        for _ in range(18):
            x = random.randint(2, W-3)
            y = random.randint(2, H-3)
            tiles[y][x] = "#"

        # Guaranteed center cross corridors
        midx, midy = W//2, H//2
        for x in range(1, W-1): tiles[midy][x] = "."
        for y in range(1, H-1): tiles[y][midx] = "."

        # Clear spawn
        spawn = [2, 2]
        for yy in range(spawn[1], min(spawn[1]+2, H)):
            for xx in range(spawn[0], min(spawn[0]+2, W)):
                tiles[yy][xx] = "."

        # Scatter coins on open tiles (avoid walls/spawn)
        placed = set()
        def is_open(x,y): return tiles[y][x] == "." and (x,y) not in placed and (x,y) != tuple(spawn)
        coins = []
        for _ in range(8):
            for _try in range(50):
                x, y = random.randint(1, W-2), random.randint(1, H-2)
                if is_open(x,y):
                    coins.append({"type":"coin","x":x,"y":y})
                    placed.add((x,y)); break

        objects = coins + [
            {"type":"sign","x":8,"y":3,"text":"Collect all coins, then ESC to quit."}
        ]

        level = {"name": name, "tiles": tiles, "player_spawn": spawn, "objects": objects}
        p = f"assets/{project}_level_{name}.json"
        self._write_json(p, level)
        return {"type":"level", "path": p, "summary": f"Level {name} with coins/signs generated."}


    def _generate_npcs(self, project:str):
        npcs = [
            {"id":"guide_v1","name":"Astra","role":"guide","x":6,"y":6},
            {"id":"merchant_v1","name":"Roux","role":"merchant","x":11,"y":7}
        ]
        p = f"assets/{project}_npcs.json"
        self._write_json(p, npcs)
        return {"type":"npcs", "path": p, "summary": "Basic NPCs created."}

    def _write_dialogue(self, project:str):
        dlg = {
            "guide_v1":[
                {"who":"Astra","text":"Welcome to Eclipsera!"},
                {"who":"Astra","text":"Move with WASD or arrows."},
                {"who":"Astra","text":"Press E to talk. Press SPACE to advance."}
            ],
            "merchant_v1":[
                {"who":"Roux","text":"I trade tips for coins… when we add inventory 😉"}
            ]
        }
        p = f"assets/{project}_dialogue.json"
        self._write_json(p, dlg)
        return {"type":"dialogue","path":p,"summary":"Dialogue written."}

    def _write_json(self, path, obj):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
