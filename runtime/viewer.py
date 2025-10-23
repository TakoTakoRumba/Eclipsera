import json, os, pygame, random

TILE = 32
PLAYER_SIZE = 24
WALL = "#"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def rect_for_grid(x, y, tile=TILE, w=TILE, h=TILE):
    return pygame.Rect(x*tile, y*tile, w, h)

# --- NPC with idle wander + anti-sticking + correct facing ---
class NPC:
    def __init__(self, data):
        self.id = data["id"]
        self.name = data.get("name", self.id)
        self.grid_x = data["x"]
        self.grid_y = data["y"]
        self.rect = rect_for_grid(self.grid_x, self.grid_y)
        # subpixel position for smooth slow movement
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)
        self.speed = 1.2
        self.cooldown = 0
        self.dir = (0, 0)      # (-1,0,1)
        self.facing = (0, 1)   # draw hint (down)

    def _choose_new_intention(self):
        # more idling than walking for natural feel
        choices = [(0,0)]*6 + [(1,0), (-1,0), (0,1), (0,-1)]
        self.dir = random.choice(choices)
        self.cooldown = random.randint(30, 90)

    def update(self, can_move_fn, stop=False):
        if stop:
            self.dir = (0, 0)
            self.cooldown = 15
            return

        if self.cooldown <= 0:
            self._choose_new_intention()

        dx = self.dir[0] * self.speed
        dy = self.dir[1] * self.speed
        moved_any = False

        # axis-separated small steps; ignore my own id during collision
        if dx:
            step_x = 1 if dx > 0 else -1
            if can_move_fn(self.rect, step_x, 0, ignore_id=self.id):
                self.pos_x += dx
                self.rect.x = int(round(self.pos_x))
                moved_any = True
        if dy:
            step_y = 1 if dy > 0 else -1
            if can_move_fn(self.rect, 0, step_y, ignore_id=self.id):
                self.pos_y += dy
                self.rect.y = int(round(self.pos_y))
                moved_any = True

        if moved_any and self.dir != (0,0):
            self.facing = self.dir
        else:
            # if blocked, force a re-pick next frame
            self.cooldown = 0

        self.cooldown -= 1

    def face_toward(self, target_center):
        cx, cy = self.rect.center
        tx, ty = target_center
        dx, dy = (tx - cx), (ty - cy)
        # Correct Y: screen Y grows downward, so "up" is dy < 0
        if abs(dx) > abs(dy):
            self.facing = (1, 0) if dx > 0 else (-1, 0)
        else:
            self.facing = (0, -1) if dy < 0 else (0, 1)

def run_viewer(project: str):
    level_path = f"assets/{project}_level_meadow_v1.json"
    npcs_path  = f"assets/{project}_npcs.json"
    dialogue_path = f"assets/{project}_dialogue.json"

    if not (os.path.exists(level_path) and os.path.exists(npcs_path)):
        print("No generated assets yet. Run: python run.py --viewer")
        return

    lvl = load_json(level_path)
    npcs_data = load_json(npcs_path)
    dialogue = load_json(dialogue_path) if os.path.exists(dialogue_path) else {}

    pygame.init()
    font = pygame.font.SysFont(None, 20)
    big  = pygame.font.SysFont(None, 28)

    tiles = lvl["tiles"]
    rows, cols = len(tiles), len(tiles[0])
    w, h = cols*TILE, rows*TILE
    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption("Eclipsera Viewer — WASD/arrows move • E talk/read • SPACE next • ESC quit")

    # Walls
    wall_rects = [rect_for_grid(x, y) for y, row in enumerate(tiles) for x, c in enumerate(row) if c == WALL]

    # Objects (coins + signs)
    objects = lvl.get("objects", [])

    # NPCs
    npcs = [NPC(d) for d in npcs_data]
    npc_map = {n.id: n for n in npcs}

    # Player (centered inside tile)
    px, py = lvl["player_spawn"]
    player = pygame.Rect(px*TILE + (TILE-PLAYER_SIZE)//2,
                         py*TILE + (TILE-PLAYER_SIZE)//2,
                         PLAYER_SIZE, PLAYER_SIZE)
    speed = 3

    # Dialogue/sign state
    talking_to = None
    dlg_index = 0
    is_dialogue_open = False
    sign_buffer = []

    # Coins/HUD
    coins_total = sum(1 for o in objects if o["type"] == "coin")
    coins_collected = 0
    win = False

    clock = pygame.time.Clock()

    def can_move(rect, dx, dy, ignore_id=None):
        trial = rect.move(dx, dy)
        # walls
        for wrect in wall_rects:
            if trial.colliderect(wrect):
                return False
        # npcs (other than me if I'm an npc)
        for n in npcs:
            if ignore_id is not None and n.id == ignore_id:
                continue
            if trial.colliderect(n.rect):
                return False
        # player blocks npcs too
        if ignore_id is not None and trial.colliderect(player):
            return False
        # bounds
        if trial.left < 0 or trial.top < 0 or trial.right > w or trial.bottom > h:
            return False
        return True

    def player_can_move(dx, dy):
        trial = player.move(dx, dy)
        for wrect in wall_rects:
            if trial.colliderect(wrect): return False
        for n in npcs:
            if trial.colliderect(n.rect): return False
        if not (0 <= trial.left and 0 <= trial.top and trial.right <= w and trial.bottom <= h):
            return False
        return True

    def nearest_npc(rect, max_dist=36):
        nearest, best = None, 1e9
        cx, cy = rect.center
        for n in npcs:
            nx, ny = n.rect.center
            d = ((cx-nx)**2 + (cy-ny)**2) ** 0.5
            if d < best and d <= max_dist:
                best, nearest = d, n
        return nearest

    def nearest_sign(rect, max_dist=36):
        nearest, best = None, 1e9
        cx, cy = rect.center
        for obj in objects:
            if obj["type"] != "sign": continue
            orect = rect_for_grid(obj["x"], obj["y"])
            ox, oy = orect.center
            d = ((cx-ox)**2 + (cy-oy)**2) ** 0.5
            if d < best and d <= max_dist:
                best, nearest = d, obj
        return nearest

    def wrap_text(text, max_px):
        words, lines, cur = text.split(), [], ""
        while words:
            nxt = (cur + " " + words[0]).strip()
            if big.size(nxt)[0] <= max_px:
                cur = nxt; words.pop(0)
            else:
                lines.append(cur); cur = ""
        if cur: lines.append(cur)
        return lines

    def draw_world():
        screen.fill((24,24,24))
        # grid
        for y in range(rows):
            for x in range(cols):
                pygame.draw.rect(screen, (58,58,58), rect_for_grid(x, y), 1)
        # walls
        for wr in wall_rects:
            pygame.draw.rect(screen, (90,90,90), wr)
        # objects
        for obj in objects:
            r = rect_for_grid(obj["x"], obj["y"])
            if obj["type"] == "coin":
                pygame.draw.rect(screen, (220,200,40), r)
            elif obj["type"] == "sign":
                pygame.draw.rect(screen, (0,150,200), r)

        # npcs + name + facing notch
        for n in npcs:
            pygame.draw.rect(screen, (200,80,80), n.rect)
            name_surf = font.render(n.name, True, (230,230,230))
            screen.blit(name_surf, (n.rect.x, n.rect.y-18))
            fx, fy = n.facing
            notch = n.rect.copy()
            if fx == 1:   notch = pygame.Rect(n.rect.right-4, n.rect.y+10, 4, 12)
            if fx == -1:  notch = pygame.Rect(n.rect.left,      n.rect.y+10, 4, 12)
            if fy == 1:   notch = pygame.Rect(n.rect.x+10,      n.rect.bottom-4, 12, 4)
            if fy == -1:  notch = pygame.Rect(n.rect.x+10,      n.rect.top,       12, 4)
            pygame.draw.rect(screen, (255,180,180), notch)

        # player
        pygame.draw.rect(screen, (220,220,220), player)

        # HUD
        hud = big.render(f"Coins: {coins_collected}/{coins_total}", True, (255,255,255))
        screen.blit(hud, (8, 6))
        if win:
            banner = big.render("All coins collected! ESC to quit.", True, (255,255,255))
            screen.blit(banner, (w//2 - banner.get_width()//2, 8))

    def draw_dialogue_box(lines, who=None):
        box = pygame.Surface((w - 24, 110), pygame.SRCALPHA)
        box.fill((0, 0, 0, 200))
        screen.blit(box, (12, h - 122))
        y = h - 116
        if who:
            who_s = big.render(who, True, (255,255,255))
            screen.blit(who_s, (24, y)); y += 28
        for L in lines[:3]:
            s = font.render(L, True, (230,230,230))
            screen.blit(s, (24, y)); y += 22
        hint = font.render("SPACE: next • ESC: close", True, (180,180,180))
        screen.blit(hint, (w - hint.get_width() - 20, h - 28))

    # --- main loop ---
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if is_dialogue_open:
                        is_dialogue_open = False
                        talking_to = None
                        sign_buffer = []
                    else:
                        pygame.quit(); return
                elif e.key == pygame.K_e and not is_dialogue_open:
                    npc = nearest_npc(player)
                    if npc:
                        talking_to = npc.id; dlg_index = 0; is_dialogue_open = True
                        npc.face_toward(player.center)
                    else:
                        sign = nearest_sign(player)
                        if sign:
                            talking_to = "SIGN"
                            sign_buffer = wrap_text(sign.get("text","(blank)"), w - 48)
                            dlg_index = 0
                            is_dialogue_open = True
                elif e.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if is_dialogue_open:
                        if talking_to == "SIGN":
                            is_dialogue_open = False; talking_to = None; sign_buffer = []
                        elif talking_to in dialogue:
                            dlg_index += 1
                            if dlg_index >= len(dialogue[talking_to]):
                                is_dialogue_open = False; talking_to = None

        keys = pygame.key.get_pressed()
        if not is_dialogue_open and not win:
            dx = dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:   dx -= speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:  dx += speed
            if keys[pygame.K_UP] or keys[pygame.K_w]:     dy -= speed
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:   dy += speed
            if dx and player_can_move(dx, 0): player.move_ip(dx, 0)
            if dy and player_can_move(0, dy): player.move_ip(0, dy)

            # coin pickup
            remaining = []
            for obj in objects:
                if obj["type"] != "coin":
                    remaining.append(obj); continue
                if player.colliderect(rect_for_grid(obj["x"], obj["y"])):
                    coins_collected += 1
                else:
                    remaining.append(obj)
            objects = remaining
            if coins_collected >= coins_total and coins_total > 0:
                win = True

        # update NPCs
        for n in npcs:
            n.update(can_move, stop=(is_dialogue_open and talking_to == n.id))

        # draw
        draw_world()
        if is_dialogue_open:
            if talking_to == "SIGN":
                draw_dialogue_box(sign_buffer)
            elif talking_to in dialogue:
                line = dialogue[talking_to][dlg_index]
                lines = wrap_text(line.get("text",""), w - 48)
                draw_dialogue_box(lines, who=line.get("who","???"))

        pygame.display.flip()
        clock.tick(60)
