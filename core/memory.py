import json, os

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
