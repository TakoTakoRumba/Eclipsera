class WorkerAgent:
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
