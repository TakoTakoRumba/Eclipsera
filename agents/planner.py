class PlannerAgent:
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
