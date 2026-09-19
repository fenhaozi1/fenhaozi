import pygame
import sys
import math
import random

# ---------- 初始化 ----------
pygame.init()
WIDTH, HEIGHT = 1100, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("一箭又一箭 · 海洋版")
clock = pygame.time.Clock()
FPS = 60

# ---------- 颜色 ----------
WHITE = (237, 242, 255)
GRAY = (143, 156, 192)
BLUE = (104, 196, 255)
RED = (255, 96, 112)
GREEN = (110, 231, 160)
YELLOW = (247, 212, 74)
DARK_BTN = (62, 71, 98)
DARK_SHADOW = (35, 42, 60)
BTN_BLUE = (61, 116, 224)
BTN_BLUE_SHADOW = (31, 61, 117)

FIREWORK_PALETTE = [
    (255, 80, 120), (255, 180, 60), (110, 231, 160),
    (104, 196, 255), (200, 120, 255), (255, 240, 100),
    (255, 120, 200), (100, 255, 220),
]

# ---------- 字体加载 ----------
def load_font(size):
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for path in candidates:
        try:
            return pygame.font.Font(path, size)
        except Exception:
            continue
    return pygame.font.Font(None, size)

font_large = load_font(72)
font_mid = load_font(30)
font_small = load_font(22)
font_tiny = load_font(18)

# ---------- 带描边的文字渲染 ----------
def render_text(font, text, color, outline_color=(0, 0, 0), outline_size=3):
    base = font.render(text, True, color)
    outline = font.render(text, True, outline_color)
    w, h = base.get_size()
    surf = pygame.Surface((w + outline_size * 2, h + outline_size * 2),
                          pygame.SRCALPHA)
    for dx in range(-outline_size, outline_size + 1):
        for dy in range(-outline_size, outline_size + 1):
            if dx == 0 and dy == 0:
                continue
            surf.blit(outline, (outline_size + dx, outline_size + dy))
    surf.blit(base, (outline_size, outline_size))
    return surf


def blit_center(surf, text_surf, y):
    surf.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, y))

# ---------- 方向映射 ----------
DIRS = {
    'U': (0, -1, 0),
    'D': (0, 1, math.pi),
    'L': (-1, 0, -math.pi / 2),
    'R': (1, 0, math.pi / 2)
}

# ---------- 关卡数据 ----------
LEVELS = [
    ["R.D", "L..", ".U."],
    [".R.D", "....", "L.U.", "...R"],
    [".R..D", "...U.", "L....", "..D..", "...LR"],
    [".U.U.",
     "L.R.D",
     ".U.D.",
     "D.L.R",
     ".R.R."]
]

MAX_MISTAKES = 3

# ---------- 游戏状态 ----------
STATE_MENU = "menu"
STATE_PLAY = "play"
STATE_CONFIRM = "confirm"
STATE_WIN = "win"
STATE_FAIL = "fail"
STATE_ALL = "allclear"

state = STATE_MENU
level_idx = 0
grid = []
rows = cols = 0
cell_size = 0
board_x = board_y = board_w = board_h = 0
mistakes_left = MAX_MISTAKES
flying_arrows = []
fail_delay = 0
win_timer = 0

level_start_time = 0
elapsed_time = 0
total_time = 0

# ---------- 海洋背景元素 ----------
bubbles = []
for _ in range(40):
    bubbles.append({
        'x': random.randint(0, WIDTH),
        'y': random.randint(0, HEIGHT),
        'r': random.randint(2, 6),
        'speed': random.uniform(15, 50),
        'sway': random.uniform(0, math.pi * 2),
    })

bg_fishes = []
for _ in range(6):
    bg_fishes.append({
        'x': random.randint(0, WIDTH),
        'y': random.randint(60, HEIGHT - 100),
        'speed': random.uniform(20, 60),
        'size': random.uniform(0.6, 1.2),
        'color': random.choice([
            (255, 180, 100), (255, 130, 160), (140, 220, 255),
            (255, 220, 120), (200, 150, 255),
        ]),
        'phase': random.uniform(0, math.pi * 2),
    })

seaweeds = []
for _ in range(8):
    seaweeds.append({
        'x': random.randint(20, WIDTH - 20),
        'height': random.randint(60, 140),
        'width': random.randint(6, 12),
        'color': random.choice([
            (40, 140, 110), (60, 160, 120), (30, 120, 90),
        ]),
        'phase': random.uniform(0, math.pi * 2),
    })

ocean_time = 0

# ---------- 海洋背景绘制 ----------
def draw_ocean_background(surf, t):
    # 1. 渐变蓝
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(10 + 20 * ratio)
        g = int(55 + 65 * ratio)
        b = int(100 + 85 * ratio)
        pygame.draw.line(surf, (r, g, b), (0, y), (WIDTH, y))

    # 2. 柔和光柱
    for i in range(5):
        light_x = 100 + i * 220 + math.sin(t * 0.5 + i) * 30
        light_surf = pygame.Surface((80, HEIGHT), pygame.SRCALPHA)
        for yy in range(HEIGHT):
            a = max(0, int(12 * (1 - yy / HEIGHT)))
            pygame.draw.line(light_surf, (180, 230, 255, a),
                             (0, yy), (80, yy))
        surf.blit(light_surf, (light_x, 0))

    # 3. 波浪
    for wave_y, wave_color, amp in [
        (30, (120, 190, 230), 6),
        (55, (100, 170, 210), 4),
    ]:
        pts = []
        for x in range(0, WIDTH + 10, 8):
            offset = math.sin(x * 0.02 + t * 1.5) * amp
            pts.append((x, wave_y + offset))
        if len(pts) > 1:
            pygame.draw.lines(surf, wave_color, False, pts, 2)

    # 4. 海草
    for sw in seaweeds:
        base_x = sw['x']
        base_y = HEIGHT - 10
        segs = 8
        sway = math.sin(t * 1.2 + sw['phase']) * 12
        prev = (base_x, base_y)
        for i in range(1, segs + 1):
            k = i / segs
            seg_x = base_x + sway * k * k
            seg_y = base_y - sw['height'] * k
            pygame.draw.line(surf, sw['color'], prev, (seg_x, seg_y),
                             max(1, int(sw['width'] * (1 - k * 0.6))))
            prev = (seg_x, seg_y)

    # 5. 背景小鱼
    for f in bg_fishes:
        draw_background_fish(surf, f, t)

    # 6. 气泡
    for b in bubbles:
        bx = b['x'] + math.sin(t * 1.5 + b['sway']) * 8
        by = b['y']
        r = b['r']
        s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (200, 240, 255, 90), (r + 1, r + 1), r)
        pygame.draw.circle(s, (240, 255, 255, 160), (r + 1, r + 1), r, 1)
        surf.blit(s, (int(bx - r), int(by - r)))


def update_ocean(dt):
    global ocean_time
    ocean_time += dt
    for b in bubbles:
        b['y'] -= b['speed'] * dt
        if b['y'] < -10:
            b['y'] = HEIGHT + 10
            b['x'] = random.randint(0, WIDTH)
    # ★ 鱼改成向左游（与鱼脸朝左的形象一致）
    for f in bg_fishes:
        f['x'] -= f['speed'] * dt
        if f['x'] < -40:
            f['x'] = WIDTH + 40
            f['y'] = random.randint(60, HEIGHT - 100)


def draw_background_fish(surf, f, t):
    x = f['x']
    y = f['y'] + math.sin(t * 2 + f['phase']) * 6
    s = f['size']
    color = f['color']
    body_w = int(22 * s)
    body_h = int(12 * s)
    body_rect = pygame.Rect(x - body_w // 2, y - body_h // 2, body_w, body_h)
    pygame.draw.ellipse(surf, color, body_rect)
    tail_pts = [
        (x + body_w // 2, y),
        (x + body_w // 2 + int(10 * s), y - int(8 * s)),
        (x + body_w // 2 + int(10 * s), y + int(8 * s)),
    ]
    pygame.draw.polygon(surf, color, tail_pts)
    pygame.draw.circle(surf, (30, 30, 30),
                       (int(x - body_w * 0.25), int(y - body_h * 0.15)),
                       max(1, int(2 * s)))
    pygame.draw.polygon(surf, color, [
        (x, y - body_h // 2),
        (x - int(6 * s), y - body_h // 2 - int(6 * s)),
        (x + int(6 * s), y - body_h // 2),
    ])


# ---------- 烟花 ----------
fireworks = []
spawn_timer = 0

def spawn_ring_burst(cx, cy, color, num=36, speed_min=100, speed_max=260,
                     life_min=0.9, life_max=1.8):
    for i in range(num):
        angle = (2 * math.pi * i / num) + random.uniform(-0.05, 0.05)
        speed = random.uniform(speed_min, speed_max)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        life = random.uniform(life_min, life_max)
        r = max(0, min(255, color[0] + random.randint(-25, 25)))
        g = max(0, min(255, color[1] + random.randint(-25, 25)))
        b = max(0, min(255, color[2] + random.randint(-25, 25)))
        fireworks.append({
            'x': cx, 'y': cy, 'vx': vx, 'vy': vy,
            'color': (r, g, b), 'life': life, 'max_life': life,
            'size': random.uniform(2.2, 4.5), 'trail': [],
        })

def spawn_scatter_burst(cx, cy, color, num=18):
    for _ in range(num):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(40, 220)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        life = random.uniform(0.5, 1.2)
        fireworks.append({
            'x': cx, 'y': cy, 'vx': vx, 'vy': vy,
            'color': color, 'life': life, 'max_life': life,
            'size': random.uniform(1.8, 3.5), 'trail': [],
        })

def create_firework():
    cx = random.randint(180, WIDTH - 180)
    cy = random.randint(80, 300)
    main_color = random.choice(FIREWORK_PALETTE)
    spawn_ring_burst(cx, cy, main_color, num=40,
                     speed_min=120, speed_max=280,
                     life_min=0.9, life_max=1.8)
    for _ in range(random.randint(1, 2)):
        ox = cx + random.randint(-50, 50)
        oy = cy + random.randint(-50, 50)
        sub_color = random.choice(FIREWORK_PALETTE)
        while sub_color == main_color:
            sub_color = random.choice(FIREWORK_PALETTE)
        spawn_scatter_burst(ox, oy, sub_color, num=random.randint(10, 18))

def update_fireworks(dt):
    global fireworks
    for p in fireworks:
        p['trail'].append((p['x'], p['y']))
        if len(p['trail']) > 6:
            p['trail'].pop(0)
        p['x'] += p['vx'] * dt
        p['y'] += p['vy'] * dt
        p['vy'] += 130 * dt
        p['vx'] *= 0.97
        p['vy'] *= 0.97
        p['life'] -= dt
    fireworks = [p for p in fireworks if p['life'] > 0]

def draw_fireworks(surf):
    for p in fireworks:
        alpha = max(0, p['life'] / p['max_life'])
        if alpha > 0.7:
            k = (1 - alpha) / 0.3
            r = int(p['color'][0] + (255 - p['color'][0]) * (1 - k))
            g = int(p['color'][1] + (255 - p['color'][1]) * (1 - k))
            b = int(p['color'][2] + (255 - p['color'][2]) * (1 - k))
        else:
            k = alpha / 0.7
            r = int(p['color'][0] * k)
            g = int(p['color'][1] * k)
            b = int(p['color'][2] * k)
        trail = p['trail']
        for i, (tx, ty) in enumerate(trail):
            t_alpha = (i + 1) / len(trail) * alpha * 0.55
            t_size = max(1, int(p['size'] * (i + 1) / len(trail) * 0.7))
            s = pygame.Surface((t_size * 2, t_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (r, g, b, int(255 * t_alpha)),
                               (t_size, t_size), t_size)
            surf.blit(s, (int(tx - t_size), int(ty - t_size)))
        size = max(1, int(p['size'] * alpha))
        if size > 0:
            glow_size = size * 2
            glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (r, g, b, int(60 * alpha)),
                               (glow_size, glow_size), glow_size)
            surf.blit(glow, (int(p['x'] - glow_size), int(p['y'] - glow_size)))
            core = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(core, (r, g, b, int(255 * alpha)),
                               (size, size), size)
            surf.blit(core, (int(p['x'] - size), int(p['y'] - size)))


# ---------- 箭头类 ----------
class Arrow:
    def __init__(self, r, c, d):
        self.r = r
        self.c = c
        self.dir = d
        self.dx, self.dy, self.angle = DIRS[d]
        self.anim = None
        self.t = 0
        self.dur = 0
        self.dist = 0
        self.offx = 0
        self.offy = 0
        self.alpha = 1
        self.color = None

# ---------- 工具函数 ----------
def load_level(idx):
    global level_idx, grid, rows, cols, cell_size, board_x, board_y, board_w, board_h
    global mistakes_left, flying_arrows, fail_delay, win_timer
    global level_start_time, elapsed_time
    level_idx = idx
    layout = LEVELS[idx]
    rows = len(layout)
    cols = max(len(row) for row in layout)
    grid = [[None]*cols for _ in range(rows)]
    for r in range(rows):
        for c in range(len(layout[r])):
            ch = layout[r][c]
            if ch in DIRS:
                grid[r][c] = Arrow(r, c, ch)
    mistakes_left = MAX_MISTAKES
    flying_arrows = []
    fail_delay = 0
    win_timer = 0
    level_start_time = pygame.time.get_ticks() / 1000.0
    elapsed_time = 0
    compute_board()

def compute_board():
    global cell_size, board_x, board_y, board_w, board_h
    area_w, area_h = 600, 480
    area_x, area_y = 80, (HEIGHT - area_h)//2
    cell_size = min(area_w//cols, area_h//rows, 110)
    board_w = cell_size * cols
    board_h = cell_size * rows
    board_x = area_x + (area_w - board_w)//2
    board_y = area_y + (area_h - board_h)//2

def center(r, c):
    return (board_x + c*cell_size + cell_size//2,
            board_y + r*cell_size + cell_size//2)

def cell_at(mx, my):
    if not (board_x <= mx < board_x+board_w and board_y <= my < board_y+board_h):
        return None
    c = (mx - board_x)//cell_size
    r = (my - board_y)//cell_size
    if 0 <= r < rows and 0 <= c < cols:
        return r, c
    return None

def blocked(arrow):
    r = arrow.r + arrow.dy
    c = arrow.c + arrow.dx
    while 0 <= r < rows and 0 <= c < cols:
        if grid[r][c] is not None:
            return True
        r += arrow.dy
        c += arrow.dx
    return False

def remaining():
    n = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c]:
                n += 1
    return n

def start_fly(arrow):
    x, y = center(arrow.r, arrow.c)
    if arrow.dx == 1:
        dist = (board_x + board_w - x) + cell_size
    elif arrow.dx == -1:
        dist = (x - board_x) + cell_size
    elif arrow.dy == 1:
        dist = (board_y + board_h - y) + cell_size
    else:
        dist = (y - board_y) + cell_size
    arrow.anim = 'fly'
    arrow.t = 0
    arrow.dur = 0.42
    arrow.dist = dist
    grid[arrow.r][arrow.c] = None
    flying_arrows.append(arrow)

def draw_arrow(surf, arrow, cx, cy, size, color, alpha):
    angle = arrow.angle
    shape = [(0, -0.46), (0.32, -0.05), (0.14, -0.05), (0.14, 0.46),
             (-0.14, 0.46), (-0.14, -0.05), (-0.32, -0.05)]
    pts = []
    for px, py in shape:
        px *= size
        py *= size
        rx = px * math.cos(angle) - py * math.sin(angle)
        ry = px * math.sin(angle) + py * math.cos(angle)
        pts.append((cx + rx, cy + ry))
    if alpha > 0.3:
        glow = pygame.Surface((int(size*2), int(size*2)), pygame.SRCALPHA)
        pygame.draw.polygon(glow, (*color[:3], int(60*alpha)),
                            [(p[0]-cx+size, p[1]-cy+size) for p in pts])
        surf.blit(glow, (cx-size, cy-size), special_flags=pygame.BLEND_ADD)
    pygame.draw.polygon(surf, (*color, int(255*alpha)), pts)
    pygame.draw.polygon(surf, (255, 255, 255, int(80*alpha)), pts, 2)

# ---------- 更新逻辑 ----------
def update(dt):
    global fail_delay, state, win_timer, elapsed_time, total_time
    for i in range(len(flying_arrows)-1, -1, -1):
        a = flying_arrows[i]
        a.t += dt
        p = min(1, a.t / a.dur)
        e = 1 - (1-p)*(1-p)
        a.offx = a.dx * a.dist * e
        a.offy = a.dy * a.dist * e
        a.alpha = max(0, 1 - p**1.6)
        if p >= 1:
            flying_arrows.pop(i)
    for r in range(rows):
        for c in range(cols):
            a = grid[r][c]
            if a and a.anim == 'bump':
                a.t += dt
                p = min(1, a.t / a.dur)
                k = math.sin(math.pi * p) * cell_size * 0.2
                a.offx = a.dx * k
                a.offy = a.dy * k
                a.color = (255, 96, 112) if p > 0.5 else (104, 196, 255)
                if p >= 1:
                    a.anim = None
                    a.offx = a.offy = 0
                    a.color = None

    if state != STATE_PLAY:
        return

    elapsed_time = (pygame.time.get_ticks() / 1000.0) - level_start_time

    if fail_delay > 0:
        fail_delay -= dt
        if fail_delay <= 0:
            state = STATE_FAIL
        return

    if remaining() == 0 and not flying_arrows:
        win_timer += dt
        if win_timer >= 0.25:
            win_timer = 0
            total_time += elapsed_time
            if level_idx + 1 < len(LEVELS):
                state = STATE_WIN
            else:
                state = STATE_ALL

# ---------- 绘制函数 ----------
def draw_menu():
    draw_ocean_background(screen, ocean_time)

    panel = pygame.Surface((760, 480), pygame.SRCALPHA)
    panel.fill((5, 25, 50, 170))
    screen.blit(panel, (WIDTH//2 - 380, 60))
    pygame.draw.rect(screen, (120, 190, 240),
                     (WIDTH//2 - 380, 60, 760, 480), 2, border_radius=20)

    title_surf = render_text(font_large, "一箭又一箭",
                             (255, 245, 200), (10, 30, 60), 4)
    blit_center(screen, title_surf, 100)

    sub_surf = render_text(font_mid, "点掉所有箭头，别被挡住",
                           (220, 240, 255), (10, 30, 60), 3)
    blit_center(screen, sub_surf, 205)

    rules = [
        "规则 ① 点击箭头，若前方无其他箭头，就会飞出棋盘",
        "规则 ② 若前方有箭头阻挡，则无法消除，失误次数减一",
        "规则 ③ 清空全部箭头通关，失误用完则失败"
    ]
    for i, rule in enumerate(rules):
        rule_surf = render_text(font_tiny, rule, (230, 245, 255),
                                (10, 30, 60), 2)
        blit_center(screen, rule_surf, 285 + i * 40)

    btn = pygame.Rect(WIDTH//2-140, 440, 280, 70)
    pygame.draw.rect(screen, (40, 130, 180), btn, border_radius=20)
    pygame.draw.rect(screen, (20, 70, 110), btn, 4, border_radius=20)
    txt_surf = render_text(font_mid, "开始游戏", WHITE, (10, 30, 60), 2)
    screen.blit(txt_surf, (WIDTH//2 - txt_surf.get_width()//2, 452))
    return btn

def draw_game():
    draw_ocean_background(screen, ocean_time)

    pad = 16
    pygame.draw.rect(screen, (30, 60, 90),
                     (board_x - pad - 4, board_y - pad - 4,
                      board_w + pad * 2 + 8, board_h + pad * 2 + 8),
                     border_radius=22)
    pygame.draw.rect(screen, (215, 195, 150),
                     (board_x - pad, board_y - pad,
                      board_w + pad * 2, board_h + pad * 2),
                     border_radius=18)
    pygame.draw.rect(screen, (240, 225, 180),
                     (board_x - pad, board_y - pad,
                      board_w + pad * 2, board_h + pad * 2),
                     3, border_radius=18)

    for r in range(rows):
        for c in range(cols):
            x = board_x + c * cell_size
            y = board_y + r * cell_size
            seed = (r * 31 + c * 17) % 20
            base = 200 + seed - 10
            cell_color = (base + 15, base, base - 50)
            pygame.draw.rect(screen, cell_color,
                             (x + 3, y + 3, cell_size - 6, cell_size - 6),
                             border_radius=10)
            pygame.draw.rect(screen, (170, 150, 110),
                             (x + 3, y + 3, cell_size - 6, cell_size - 6),
                             2, border_radius=10)

    for r in range(rows):
        for c in range(cols):
            a = grid[r][c]
            if a:
                cx, cy = center(r, c)
                cx += a.offx
                cy += a.offy
                color = a.color if a.color else (100, 200, 255)
                draw_arrow(screen, a, cx, cy, cell_size*0.7, color, a.alpha)
    for a in flying_arrows:
        cx, cy = center(a.r, a.c)
        cx += a.offx
        cy += a.offy
        color = a.color if a.color else (100, 200, 255)
        draw_arrow(screen, a, cx, cy, cell_size*0.7, color, a.alpha)

    info_x = 780
    panel_rect = pygame.Rect(info_x - 20, 30, 260, 400)
    panel_surf = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
    panel_surf.fill((15, 45, 85, 230))
    screen.blit(panel_surf, (panel_rect.x, panel_rect.y))
    pygame.draw.rect(screen, (110, 190, 240),
                     panel_rect, 2, border_radius=16)

    t = render_text(font_mid, f"第 {level_idx+1} 关 / 共 {len(LEVELS)} 关",
                    (220, 240, 255), (5, 20, 40), 2)
    screen.blit(t, (info_x, 60))
    t = render_text(font_mid, f"剩余箭头: {remaining()}",
                    (120, 255, 200), (5, 20, 40), 2)
    screen.blit(t, (info_x, 120))
    t = render_text(font_small, "剩余失误:", (200, 225, 250), (5, 20, 40), 2)
    screen.blit(t, (info_x, 180))

    for i in range(MAX_MISTAKES):
        color = (255, 100, 120) if i < mistakes_left else (60, 80, 110)
        pygame.draw.circle(screen, color, (info_x + 20 + i*40, 230), 12)
        pygame.draw.circle(screen, (150, 200, 240), (info_x + 20 + i*40, 230), 12, 2)

    t = render_text(font_small, f"用时: {elapsed_time:.1f}s",
                    (255, 230, 120), (5, 20, 40), 2)
    screen.blit(t, (info_x, 280))

    btn_restart = pygame.Rect(info_x, 340, 170, 50)
    pygame.draw.rect(screen, (40, 100, 150), btn_restart, border_radius=12)
    pygame.draw.rect(screen, (20, 60, 100), btn_restart, 3, border_radius=12)
    t = render_text(font_small, "重新开始本关", WHITE, (5, 20, 40), 2)
    screen.blit(t, (info_x + 15, 350))
    return btn_restart

def draw_confirm():
    draw_ocean_background(screen, ocean_time)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 20, 40, 200))
    screen.blit(overlay, (0, 0))

    title = render_text(font_mid, "确定要重新开始本关吗？",
                        (240, 250, 255), (5, 20, 40), 3)
    blit_center(screen, title, 195)
    sub = render_text(font_small, "当前关卡的进度会丢失，失误次数会恢复到 3 次。",
                      (200, 225, 250), (5, 20, 40), 2)
    blit_center(screen, sub, 268)

    btn1 = pygame.Rect(WIDTH//2-220, 350, 200, 60)
    btn2 = pygame.Rect(WIDTH//2+20, 350, 200, 60)
    pygame.draw.rect(screen, (40, 130, 180), btn1, border_radius=16)
    pygame.draw.rect(screen, (20, 70, 110), btn1, 4, border_radius=16)
    pygame.draw.rect(screen, (60, 80, 100), btn2, border_radius=16)
    pygame.draw.rect(screen, (30, 45, 60), btn2, 4, border_radius=16)
    t1 = render_text(font_small, "确定重新开始", WHITE, (5, 20, 40), 2)
    t2 = render_text(font_small, "取消", WHITE, (5, 20, 40), 2)
    screen.blit(t1, (btn1.x + (btn1.w - t1.get_width())//2, btn1.y + 12))
    screen.blit(t2, (btn2.x + (btn2.w - t2.get_width())//2, btn2.y + 12))
    return btn1, btn2

def draw_win(is_last):
    draw_ocean_background(screen, ocean_time)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 20, 40, 180))
    screen.blit(overlay, (0, 0))

    title = render_text(font_large, "关卡完成！",
                        (120, 255, 180), (5, 40, 20), 4)
    blit_center(screen, title, 145)
    sub = render_text(font_mid, f"剩余失误 {mistakes_left} · 用时 {elapsed_time:.1f}s",
                      (220, 240, 255), (5, 20, 40), 3)
    blit_center(screen, sub, 268)

    btn1 = pygame.Rect(WIDTH//2-240, 400, 220, 60)
    btn2 = pygame.Rect(WIDTH//2+20, 400, 220, 60)
    pygame.draw.rect(screen, (40, 130, 180), btn1, border_radius=16)
    pygame.draw.rect(screen, (20, 70, 110), btn1, 4, border_radius=16)
    pygame.draw.rect(screen, (60, 80, 100), btn2, border_radius=16)
    pygame.draw.rect(screen, (30, 45, 60), btn2, 4, border_radius=16)

    if is_last:
        txt1 = "查看最终结果"
    else:
        txt1 = "下一关 →"
    t1 = render_text(font_small, txt1, WHITE, (5, 20, 40), 2)
    t2 = render_text(font_small, "返回主菜单", WHITE, (5, 20, 40), 2)
    screen.blit(t1, (btn1.x + (btn1.w - t1.get_width())//2, btn1.y + 12))
    screen.blit(t2, (btn2.x + (btn2.w - t2.get_width())//2, btn2.y + 12))
    return btn1, btn2

def draw_all():
    draw_ocean_background(screen, ocean_time)
    draw_fireworks(screen)

    title = render_text(font_large, "全部通关！",
                        (255, 230, 100), (60, 40, 0), 4)
    blit_center(screen, title, 145)
    sub = render_text(font_mid, f"恭喜你完成了全部 {len(LEVELS)} 关！总用时 {total_time:.1f}s",
                      (220, 240, 255), (5, 20, 40), 3)
    blit_center(screen, sub, 268)

    btn1 = pygame.Rect(WIDTH//2-240, 400, 220, 60)
    btn2 = pygame.Rect(WIDTH//2+20, 400, 220, 60)
    pygame.draw.rect(screen, (40, 130, 180), btn1, border_radius=16)
    pygame.draw.rect(screen, (20, 70, 110), btn1, 4, border_radius=16)
    pygame.draw.rect(screen, (60, 80, 100), btn2, border_radius=16)
    pygame.draw.rect(screen, (30, 45, 60), btn2, 4, border_radius=16)
    t1 = render_text(font_small, "返回主菜单", WHITE, (5, 20, 40), 2)
    t2 = render_text(font_small, "退出游戏", WHITE, (5, 20, 40), 2)
    screen.blit(t1, (btn1.x + (btn1.w - t1.get_width())//2, btn1.y + 12))
    screen.blit(t2, (btn2.x + (btn2.w - t2.get_width())//2, btn2.y + 12))
    return btn1, btn2

def draw_fail():
    draw_ocean_background(screen, ocean_time)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 20, 40, 200))
    screen.blit(overlay, (0, 0))

    title = render_text(font_large, "游戏失败",
                        (255, 120, 140), (50, 10, 20), 4)
    blit_center(screen, title, 145)
    sub = render_text(font_mid, f"失误次数已用完（本关用时 {elapsed_time:.1f}s）",
                      (220, 240, 255), (5, 20, 40), 3)
    blit_center(screen, sub, 268)

    btn1 = pygame.Rect(WIDTH//2-240, 400, 220, 60)
    btn2 = pygame.Rect(WIDTH//2+20, 400, 220, 60)
    pygame.draw.rect(screen, (40, 130, 180), btn1, border_radius=16)
    pygame.draw.rect(screen, (20, 70, 110), btn1, 4, border_radius=16)
    pygame.draw.rect(screen, (60, 80, 100), btn2, border_radius=16)
    pygame.draw.rect(screen, (30, 45, 60), btn2, 4, border_radius=16)
    t1 = render_text(font_small, "重试本关", WHITE, (5, 20, 40), 2)
    t2 = render_text(font_small, "返回主菜单", WHITE, (5, 20, 40), 2)
    screen.blit(t1, (btn1.x + (btn1.w - t1.get_width())//2, btn1.y + 12))
    screen.blit(t2, (btn2.x + (btn2.w - t2.get_width())//2, btn2.y + 12))
    return btn1, btn2

# ---------- 主循环 ----------
running = True
last_time = pygame.time.get_ticks() / 1000.0
btn_restart = None

while running:
    now = pygame.time.get_ticks() / 1000.0
    dt = min(now - last_time, 0.05)
    last_time = now

    update_ocean(dt)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if state == STATE_MENU:
                btn = draw_menu()
                if btn.collidepoint(mx, my):
                    total_time = 0
                    fireworks = []
                    spawn_timer = 0
                    load_level(0)
                    state = STATE_PLAY

            elif state == STATE_PLAY:
                if btn_restart and btn_restart.collidepoint(mx, my):
                    state = STATE_CONFIRM
                else:
                    pos = cell_at(mx, my)
                    if pos:
                        r, c = pos
                        arrow = grid[r][c]
                        if arrow and arrow.anim is None:
                            if blocked(arrow):
                                arrow.anim = 'bump'
                                arrow.t = 0
                                arrow.dur = 0.4
                                mistakes_left -= 1
                                if mistakes_left <= 0:
                                    fail_delay = 0.7
                            else:
                                start_fly(arrow)

            elif state == STATE_CONFIRM:
                btn1, btn2 = draw_confirm()
                if btn1.collidepoint(mx, my):
                    load_level(level_idx)
                    state = STATE_PLAY
                elif btn2.collidepoint(mx, my):
                    state = STATE_PLAY

            elif state == STATE_WIN:
                is_last = (level_idx + 1 >= len(LEVELS))
                btn1, btn2 = draw_win(is_last)
                if btn1.collidepoint(mx, my):
                    if is_last:
                        state = STATE_ALL
                        fireworks = []
                        spawn_timer = 0
                    else:
                        load_level(level_idx + 1)
                        state = STATE_PLAY
                elif btn2.collidepoint(mx, my):
                    state = STATE_MENU

            elif state == STATE_FAIL:
                btn1, btn2 = draw_fail()
                if btn1.collidepoint(mx, my):
                    load_level(level_idx)
                    state = STATE_PLAY
                elif btn2.collidepoint(mx, my):
                    state = STATE_MENU

            elif state == STATE_ALL:
                btn1, btn2 = draw_all()
                if btn1.collidepoint(mx, my):
                    state = STATE_MENU
                    fireworks = []
                    spawn_timer = 0
                elif btn2.collidepoint(mx, my):
                    running = False

    if state == STATE_PLAY:
        update(dt)
    elif state == STATE_ALL:
        spawn_timer += dt
        if spawn_timer >= random.uniform(0.4, 0.8):
            spawn_timer = 0
            create_firework()
        update_fireworks(dt)

    if state == STATE_MENU:
        draw_menu()
    elif state == STATE_PLAY:
        btn_restart = draw_game()
    elif state == STATE_CONFIRM:
        draw_confirm()
    elif state == STATE_WIN:
        is_last = (level_idx + 1 >= len(LEVELS))
        draw_win(is_last)
    elif state == STATE_FAIL:
        draw_fail()
    elif state == STATE_ALL:
        draw_all()

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()