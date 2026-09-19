import pygame
import sys
import math

# ---------- 初始化 ----------
pygame.init()
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("一箭又一箭 (增加计时和确认框)")
clock = pygame.time.Clock()
FPS = 60

# ---------- 颜色 ----------
BG = (24, 31, 48)
BOARD_BG = (30, 38, 60)
CELL_BG = (37, 45, 68)
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

# ---------- 方向映射（正确版）----------
DIRS = {
    'U': (0, -1, 0),
    'D': (0, 1, math.pi),
    'L': (-1, 0, -math.pi / 2),
    'R': (1, 0, math.pi / 2)
}

# ---------- 关卡数据（第四关还是 7 箭头版）----------
LEVELS = [
    ["R.D", "L..", ".U."],
    [".R.D", "....", "L.U.", "...R"],
    [".R..D", "...U.", "L....", "..D..", "...LR"],
    ["R.U..",
     "....D",
     ".L...",
     "...U.",
     "D...R"]
]

MAX_MISTAKES = 3

# ---------- 游戏状态 ----------
STATE_MENU = "menu"
STATE_PLAY = "play"
STATE_CONFIRM = "confirm"       # ★ 新增：重开确认
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

# ★ 计时变量
level_start_time = 0
elapsed_time = 0
total_time = 0

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

    # ★ 每帧更新计时
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
    screen.fill(BG)
    title = font_large.render("一箭又一箭", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
    sub = font_mid.render("点掉所有箭头，别被挡住", True, GRAY)
    screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 200))
    rules = [
        "规则 ① 点击箭头，若前方无其他箭头，就会飞出棋盘",
        "规则 ② 若前方有箭头阻挡，则无法消除，失误次数减一",
        "规则 ③ 清空全部箭头通关，失误用完则失败"
    ]
    for i, rule in enumerate(rules):
        screen.blit(font_tiny.render(rule, True, (185, 198, 230)),
                    (WIDTH//2 - 260, 280 + i*36))
    btn = pygame.Rect(WIDTH//2-140, 440, 280, 70)
    pygame.draw.rect(screen, BTN_BLUE, btn, border_radius=20)
    pygame.draw.rect(screen, BTN_BLUE_SHADOW, btn, 4, border_radius=20)
    txt = font_mid.render("开始游戏", True, WHITE)
    screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 455))
    return btn

def draw_game():
    screen.fill(BG)
    pygame.draw.rect(screen, BOARD_BG,
                     (board_x-16, board_y-16, board_w+32, board_h+32),
                     border_radius=18)
    pygame.draw.rect(screen, (51, 64, 95),
                     (board_x-16, board_y-16, board_w+32, board_h+32),
                     2, border_radius=18)
    for r in range(rows):
        for c in range(cols):
            x = board_x + c*cell_size
            y = board_y + r*cell_size
            pygame.draw.rect(screen, CELL_BG,
                             (x+3, y+3, cell_size-6, cell_size-6),
                             border_radius=10)
            pygame.draw.rect(screen, (51, 61, 90),
                             (x+3, y+3, cell_size-6, cell_size-6),
                             1, border_radius=10)
    for r in range(rows):
        for c in range(cols):
            a = grid[r][c]
            if a:
                cx, cy = center(r, c)
                cx += a.offx
                cy += a.offy
                color = a.color if a.color else BLUE
                draw_arrow(screen, a, cx, cy, cell_size*0.7, color, a.alpha)
    for a in flying_arrows:
        cx, cy = center(a.r, a.c)
        cx += a.offx
        cy += a.offy
        color = a.color if a.color else BLUE
        draw_arrow(screen, a, cx, cy, cell_size*0.7, color, a.alpha)

    info_x = 750
    screen.blit(font_mid.render(f"第 {level_idx+1} 关 / 共 {len(LEVELS)} 关", True, WHITE), (info_x, 60))
    screen.blit(font_mid.render(f"剩余箭头: {remaining()}", True, GREEN), (info_x, 120))
    screen.blit(font_small.render("剩余失误:", True, GRAY), (info_x, 180))
    for i in range(MAX_MISTAKES):
        color = RED if i < mistakes_left else (47, 55, 80)
        pygame.draw.circle(screen, color, (info_x + 20 + i*40, 230), 12)
        pygame.draw.circle(screen, (62, 74, 107), (info_x + 20 + i*40, 230), 12, 2)

    # ★ 显示用时
    screen.blit(font_small.render(f"用时: {elapsed_time:.1f}s", True, YELLOW), (info_x, 280))

    btn_restart = pygame.Rect(info_x, 340, 170, 50)
    pygame.draw.rect(screen, DARK_BTN, btn_restart, border_radius=12)
    pygame.draw.rect(screen, DARK_SHADOW, btn_restart, 3, border_radius=12)
    screen.blit(font_small.render("重新开始本关", True, WHITE), (info_x+15, 353))
    return btn_restart

def draw_confirm():
    """★ 新增：重开确认画面"""
    screen.fill(BG)
    title = font_mid.render("确定要重新开始本关吗？", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 200))
    sub = font_small.render("当前关卡的进度会丢失，失误次数会恢复到 3 次。", True, GRAY)
    screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 270))

    btn1 = pygame.Rect(WIDTH//2-220, 350, 200, 60)
    btn2 = pygame.Rect(WIDTH//2+20, 350, 200, 60)
    pygame.draw.rect(screen, BTN_BLUE, btn1, border_radius=16)
    pygame.draw.rect(screen, BTN_BLUE_SHADOW, btn1, 4, border_radius=16)
    pygame.draw.rect(screen, DARK_BTN, btn2, border_radius=16)
    pygame.draw.rect(screen, DARK_SHADOW, btn2, 4, border_radius=16)
    t1 = font_small.render("确定重新开始", True, WHITE)
    t2 = font_small.render("取消", True, WHITE)
    screen.blit(t1, (btn1.x+50, btn1.y+18))
    screen.blit(t2, (btn2.x+80, btn2.y+18))
    return btn1, btn2

def draw_win(is_last):
    screen.fill(BG)
    title = font_large.render("关卡完成！", True, GREEN)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
    sub = font_mid.render(f"剩余失误 {mistakes_left} · 用时 {elapsed_time:.1f}s", True, GRAY)
    screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 270))

    btn1 = pygame.Rect(WIDTH//2-240, 400, 220, 60)
    btn2 = pygame.Rect(WIDTH//2+20, 400, 220, 60)
    pygame.draw.rect(screen, BTN_BLUE, btn1, border_radius=16)
    pygame.draw.rect(screen, BTN_BLUE_SHADOW, btn1, 4, border_radius=16)
    pygame.draw.rect(screen, DARK_BTN, btn2, border_radius=16)
    pygame.draw.rect(screen, DARK_SHADOW, btn2, 4, border_radius=16)

    if is_last:
        t1 = font_small.render("返回主菜单", True, WHITE)
        t2 = font_small.render("退出游戏", True, WHITE)
    else:
        t1 = font_small.render("下一关 →", True, WHITE)
        t2 = font_small.render("返回主菜单", True, WHITE)
    screen.blit(t1, (btn1.x+55, btn1.y+18))
    screen.blit(t2, (btn2.x+60, btn2.y+18))
    return btn1, btn2

def draw_all():
    screen.fill(BG)
    title = font_large.render("全部通关！", True, YELLOW)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
    sub = font_mid.render(f"恭喜你完成了全部 {len(LEVELS)} 关！总用时 {total_time:.1f}s", True, GRAY)
    screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 270))

    btn1 = pygame.Rect(WIDTH//2-240, 400, 220, 60)
    btn2 = pygame.Rect(WIDTH//2+20, 400, 220, 60)
    pygame.draw.rect(screen, BTN_BLUE, btn1, border_radius=16)
    pygame.draw.rect(screen, BTN_BLUE_SHADOW, btn1, 4, border_radius=16)
    pygame.draw.rect(screen, DARK_BTN, btn2, border_radius=16)
    pygame.draw.rect(screen, DARK_SHADOW, btn2, 4, border_radius=16)
    t1 = font_small.render("返回主菜单", True, WHITE)
    t2 = font_small.render("退出游戏", True, WHITE)
    screen.blit(t1, (btn1.x+60, btn1.y+18))
    screen.blit(t2, (btn2.x+70, btn2.y+18))
    return btn1, btn2

def draw_fail():
    screen.fill(BG)
    title = font_large.render("游戏失败", True, RED)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
    sub = font_mid.render(f"失误次数已用完（本关用时 {elapsed_time:.1f}s）", True, GRAY)
    screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 270))

    btn1 = pygame.Rect(WIDTH//2-240, 400, 220, 60)
    btn2 = pygame.Rect(WIDTH//2+20, 400, 220, 60)
    pygame.draw.rect(screen, BTN_BLUE, btn1, border_radius=16)
    pygame.draw.rect(screen, BTN_BLUE_SHADOW, btn1, 4, border_radius=16)
    pygame.draw.rect(screen, DARK_BTN, btn2, border_radius=16)
    pygame.draw.rect(screen, DARK_SHADOW, btn2, 4, border_radius=16)
    t1 = font_small.render("重试本关", True, WHITE)
    t2 = font_small.render("返回主菜单", True, WHITE)
    screen.blit(t1, (btn1.x+70, btn1.y+18))
    screen.blit(t2, (btn2.x+60, btn2.y+18))
    return btn1, btn2

# ---------- 主循环 ----------
running = True
last_time = pygame.time.get_ticks() / 1000.0
btn_restart = None

while running:
    now = pygame.time.get_ticks() / 1000.0
    dt = min(now - last_time, 0.05)
    last_time = now

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if state == STATE_MENU:
                btn = draw_menu()
                if btn.collidepoint(mx, my):
                    total_time = 0
                    load_level(0)
                    state = STATE_PLAY

            elif state == STATE_PLAY:
                if btn_restart and btn_restart.collidepoint(mx, my):
                    state = STATE_CONFIRM          # ★ 改为进入确认状态
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
                elif btn2.collidepoint(mx, my):
                    running = False

    if state == STATE_PLAY:
        update(dt)

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