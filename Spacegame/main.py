import pygame
import math
import random
import os
import asyncio  # Tarvitaan web-julkaisua varten

# --- 1. GLOBAALI ALUSTUS ---
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.init() 

SCREEN_WIDTH, SCREEN_HEIGHT = 1000, 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Avaruuden Romunkerääjä")
clock = pygame.time.Clock()

# Värit
BLACK = (5, 5, 15)
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
GREEN = (0, 255, 120)
CYAN = (0, 255, 255)
ORANGE = (255, 140, 0)
RED = (255, 50, 50)
GRAY = (100, 100, 100)
NEBULA_COLORS = [(20, 10, 40), (10, 20, 40), (30, 10, 30)]

base_path = os.path.dirname(__file__)
font = pygame.font.SysFont('Futura', 30)
small_font = pygame.font.SysFont('Futura', 22)
menu_font = pygame.font.SysFont('Futura', 70)

# --- 2. APUFUNKTIOT JA LUOKAT ---

def load_image(name, fallback_color, size):
    path = os.path.join(base_path, "assets", name)
    try:
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(img, size)
        raise FileNotFoundError
    except:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        if "asema" in name: 
            pygame.draw.circle(surf, GREEN, (size[0]//2, size[1]//2), size[0]//2, 4)
        elif "meteoriitti" in name: 
            pygame.draw.circle(surf, (80, 80, 85), (size[0]//2, size[1]//2), size[0]//2)
        elif "romu" in name:
            pts = [(size[0]//2, 0), (size[0], size[1]//2), (size[0]//2, size[1]), (0, size[1]//2)]
            pygame.draw.polygon(surf, fallback_color, pts)
        else: 
            pygame.draw.rect(surf, fallback_color, [0, 0, size[0], size[1]])
        return surf

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.original_image = load_image("pelaaja.png", CYAN, (45, 45))
        self.image = self.original_image
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
        self.vel = pygame.math.Vector2(0, 0)
        self.angle = 0
        self.attached_junk = None
        self.fuel = 100.0
        self.max_fuel = 100.0
        self.engine_power = 0.16
        self.shield = False

    def update(self, particles):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]: self.angle += 4.5
        if keys[pygame.K_d]: self.angle -= 4.5
        if keys[pygame.K_w] and self.fuel > 0:
            direction = pygame.math.Vector2(0, -1).rotate(-self.angle)
            thrust = self.engine_power
            if self.attached_junk: thrust *= self.attached_junk.weight
            self.vel += direction * thrust
            self.fuel -= 0.12 
            ex_pos = self.pos + pygame.math.Vector2(0, 18).rotate(-self.angle)
            particles.append({"pos": list(ex_pos), "vel": [-direction.x*2, -direction.y*2], "size": random.randint(4, 7), "color": list(ORANGE), "life": 1.0})
        self.vel *= 0.982 
        self.pos += self.vel
        self.pos.x %= SCREEN_WIDTH
        self.pos.y %= SCREEN_HEIGHT
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=(self.pos.x, self.pos.y))

class Junk(pygame.sprite.Sprite):
    def __init__(self, jtype="normal"):
        super().__init__()
        self.jtype = jtype
        stats = {
            "gold": (GOLD, 500, 0.35, "KULTA"),
            "fuel": (GREEN, 50, 0.85, "POLTTOAINE"),
            "radioactive": (RED, 250, 0.75, "SÄTEILY"),
            "normal": (WHITE, 100, 0.75, "ROMU")
        }
        self.color, self.points, self.weight, self.label = stats[jtype]
        self.image = load_image("romu.png", self.color, (30, 30))
        self.rect = self.image.get_rect()
        self.spawn_random()
        self.attached = False

    def spawn_random(self):
        self.pos = pygame.math.Vector2(random.randint(100, SCREEN_WIDTH-100), random.randint(100, SCREEN_HEIGHT-100))
        self.attached = False

    def update(self, player_pos, player_angle):
        if self.attached:
            target = player_pos + pygame.math.Vector2(0, 45).rotate(-player_angle)
            self.pos += (target - self.pos) * 0.15
        self.rect.center = self.pos

class Meteor(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        size = random.randint(40, 70)
        self.base_image = load_image("meteoriitti.png", (90, 85, 80), (size, size))
        self.image = self.base_image
        self.rect = self.image.get_rect()
        self.rot = 0
        self.rot_s = random.uniform(-2, 2)
        self.reset()

    def reset(self):
        side = random.choice(["T", "B", "L", "R"])
        if side == "T": self.pos = pygame.math.Vector2(random.randint(0, SCREEN_WIDTH), -100)
        elif side == "B": self.pos = pygame.math.Vector2(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT+100)
        elif side == "L": self.pos = pygame.math.Vector2(-100, random.randint(0, SCREEN_HEIGHT))
        else: self.pos = pygame.math.Vector2(SCREEN_WIDTH+100, random.randint(0, SCREEN_HEIGHT))
        target = pygame.math.Vector2(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
        self.vel = (target - self.pos).normalize() * random.uniform(1.5, 3.0)

    def update(self):
        self.pos += self.vel
        self.rot += self.rot_s
        self.image = pygame.transform.rotate(self.base_image, self.rot)
        self.rect = self.image.get_rect(center=self.pos)
        if not (-200 < self.pos.x < SCREEN_WIDTH+200 and -200 < self.pos.y < SCREEN_HEIGHT+200):
            self.reset()

class Station(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = load_image("asema.png", GREEN, (180, 180))
        self.rect = self.image.get_rect(center=(SCREEN_WIDTH - 120, 120))

def draw_text(surf, text, color, x, y, f_obj, center=False):
    img = f_obj.render(text, True, color)
    if center: x -= img.get_width() // 2
    surf.blit(img, (x, y))

# --- 3. PÄÄFUNKTIO (ASYNC) ---

async def main():
    score = 0
    high_score = 0
    game_state = "MENU"
    shake_amount = 0
    particles = []
    
    try:
        score_sound = pygame.mixer.Sound(os.path.join(base_path, "assets", "score.wav"))
        pygame.mixer.music.load(os.path.join(base_path, "assets", "music.wav"))
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
    except:
        score_sound = None

    def start_new_game():
        nonlocal score, shake_amount, particles, player, station, junk_group, meteor_group
        player = Player()
        station = Station()
        junk_group = pygame.sprite.Group()
        meteor_group = pygame.sprite.Group()
        particles = []
        score = 0
        shake_amount = 0
        for _ in range(6): junk_group.add(Junk(random.choice(["normal", "gold", "fuel", "radioactive"])))
        for _ in range(4): meteor_group.add(Meteor())
        return player, station, junk_group, meteor_group

    player, station, junk_group, meteor_group = start_new_game()
    stars = [[random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.uniform(0.5, 2.5)] for _ in range(180)]
    nebulae = [[random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.randint(150, 350), random.choice(NEBULA_COLORS)] for _ in range(6)]
    e_button_img = load_image("e_nappi.png", WHITE, (35, 35))
    display_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    shop_rects = [pygame.Rect(300, 300, 400, 65), pygame.Rect(300, 390, 400, 65), pygame.Rect(300, 480, 400, 65)]

    run = True
    while run:
        dt = clock.tick(60) / 1000.0
        display_surface.fill(BLACK)
        mouse_pos = pygame.mouse.get_pos()

        off = [0, 0]
        if shake_amount > 0:
            off = [random.randint(-int(shake_amount), int(shake_amount)) for _ in range(2)]
            shake_amount *= 0.9

        for n in nebulae:
            n[0] -= player.vel.x * 0.04; n[1] -= player.vel.y * 0.04
            n[0] %= SCREEN_WIDTH; n[1] %= SCREEN_HEIGHT
            pygame.draw.circle(display_surface, n[3], (int(n[0]), int(n[1])), n[2])
        for s in stars:
            s[0] -= player.vel.x * s[2] * 0.15; s[1] -= player.vel.y * s[2] * 0.15
            s[0] %= SCREEN_WIDTH; s[1] %= SCREEN_HEIGHT
            pygame.draw.circle(display_surface, (200, 200, 200), (int(s[0]), int(s[1])), int(s[2]))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                # --- ESC-NÄPPÄIN TÄSSÄ ---
                if event.key == pygame.K_ESCAPE:
                    game_state = "MENU"
                
                if event.key == pygame.K_SPACE and game_state in ["MENU", "GAMEOVER"]:
                    player, station, junk_group, meteor_group = start_new_game()
                    game_state = "GAME"
                if event.key == pygame.K_s:
                    if game_state == "GAME" and player.rect.colliderect(station.rect.inflate(60, 60)): game_state = "SHOP"
                    elif game_state == "SHOP": game_state = "GAME"
            
            if event.type == pygame.MOUSEBUTTONDOWN and game_state == "SHOP":
                if shop_rects[0].collidepoint(mouse_pos) and score >= 400:
                    score -= 400; player.max_fuel += 40; player.fuel = player.max_fuel
                if shop_rects[1].collidepoint(mouse_pos) and score >= 600:
                    score -= 600; player.engine_power += 0.05
                if shop_rects[2].collidepoint(mouse_pos) and score >= 800 and not player.shield:
                    score -= 800; player.shield = True

        if game_state == "MENU":
            draw_text(display_surface, "AVARUUDEN ROMUNKERÄÄJÄ", CYAN, SCREEN_WIDTH//2, 200, menu_font, True)
            draw_text(display_surface, "PELIN IDEA", WHITE, SCREEN_WIDTH//2, 80, menu_font, True)
            draw_text(display_surface, "Kerää romua ja vie se oikealla puolella olevaan asemaan ja kerää pisteitä", WHITE, SCREEN_WIDTH//2, 130, font, True)
            draw_text(display_surface, "VARO METEORIITTEJA!!", WHITE, SCREEN_WIDTH//2, 170, font, True)
            draw_text(display_surface, "Paina SPACE aloittaaksesi", GOLD, SCREEN_WIDTH//2, 300, font, True)
            
            # Valikon ohjetekstit
            instructions_y = 450
            draw_text(display_surface, "OHJEET:", WHITE, SCREEN_WIDTH//2, instructions_y, font, True)
            draw_text(display_surface, "W: Kaasu  |  A & D: Kääntyminen", WHITE, SCREEN_WIDTH//2, instructions_y + 40, small_font, True)
            draw_text(display_surface, "E: Kerää romua (kun lähellä)", WHITE, SCREEN_WIDTH//2, instructions_y + 70, small_font, True)
            draw_text(display_surface, "S: Kauppa (aseman lähellä)", WHITE, SCREEN_WIDTH//2, instructions_y + 100, small_font, True)
            draw_text(display_surface, "ESC: Palaa tähän valikkoon", WHITE, SCREEN_WIDTH//2, instructions_y + 130, small_font, True)

            if high_score > 0: 
                draw_text(display_surface, f"PARAS TULOS: {high_score}", GOLD, SCREEN_WIDTH//2, 700, font, True)
            
        elif game_state == "GAME":
            player.update(particles)
            junk_group.update(player.pos, player.angle)
            meteor_group.update()
            if score > high_score: high_score = score

            if junk_group:
                cl = min(junk_group, key=lambda j: (j.pos - player.pos).length())
                ang = math.atan2(cl.pos.y - player.pos.y, cl.pos.x - player.pos.x)
                p_rad = player.pos + pygame.math.Vector2(60, 0).rotate(math.degrees(ang))
                pygame.draw.circle(display_surface, cl.color, (int(p_rad.x), int(p_rad.y)), 5)

            for p in particles[:]:
                p["pos"][0] += p["vel"][0]; p["pos"][1] += p["vel"][1]; p["life"] -= 0.03
                if p["life"] <= 0: particles.remove(p)
                else: pygame.draw.circle(display_surface, p["color"], (int(p["pos"][0]), int(p["pos"][1])), int(p["size"]*p["life"]))

            hits = pygame.sprite.spritecollide(player, junk_group, False)
            if not player.attached_junk and hits:
                display_surface.blit(e_button_img, (hits[0].rect.centerx-17, hits[0].rect.top-35))
                if pygame.key.get_pressed()[pygame.K_e]: 
                    player.attached_junk = hits[0]
                    player.attached_junk.attached = True

            if pygame.sprite.spritecollide(player, meteor_group, False, pygame.sprite.collide_circle_ratio(0.7)):
                if player.shield: 
                    player.shield = False; shake_amount = 20
                    for m in meteor_group: m.reset()
                else: game_state = "GAMEOVER"
            
            if player.fuel <= 0: game_state = "GAMEOVER"

            display_surface.blit(station.image, station.rect)
            junk_group.draw(display_surface)
            meteor_group.draw(display_surface)
            display_surface.blit(player.image, player.rect)
            if player.shield: pygame.draw.circle(display_surface, CYAN, player.pos, 35, 2)
            
            if player.rect.colliderect(station.rect.inflate(60, 60)):
                draw_text(display_surface, "[S] KAUPPA", GREEN, station.rect.centerx, station.rect.bottom+10, font, True)

            if player.attached_junk:
                if player.attached_junk.rect.colliderect(station.rect):
                    score += player.attached_junk.points
                    if score_sound: score_sound.play()
                    player.fuel = player.max_fuel if player.attached_junk.jtype == "fuel" else min(player.max_fuel, player.fuel + 30)
                    player.attached_junk.spawn_random()
                    player.attached_junk = None
                else:
                    pygame.draw.line(display_surface, (150, 150, 150), player.pos, player.attached_junk.pos, 1)

            draw_text(display_surface, f"PISTEET: {score}", WHITE, 25, 25, font)
            pygame.draw.rect(display_surface, (40, 40, 40), [25, 65, 150, 15])
            pygame.draw.rect(display_surface, GREEN if player.fuel > 25 else RED, [25, 65, int(player.fuel/player.max_fuel*150), 15])

        elif game_state == "SHOP":
            display_surface.fill((15, 25, 35))
            draw_text(display_surface, "ASEMAN KAUPPA", GREEN, SCREEN_WIDTH//2, 80, menu_font, True)
            draw_text(display_surface, f"VARAT: {score}p", GOLD, SCREEN_WIDTH//2, 160, font, True)
            items = [("TANKKI PRO (400p)", "Lisää max polttoainetta."), ("MOOTTORI (600p)", "Lisää kiihtyvyyttä."), ("KILPI (800p)", "Kestää yhden törmäyksen.")]
            costs = [400, 600, 800]
            for i, rect in enumerate(shop_rects):
                can_buy = score >= costs[i]
                bg_col = (40, 60, 80) if rect.collidepoint(mouse_pos) and can_buy else (20, 30, 45)
                pygame.draw.rect(display_surface, bg_col, rect, 0, 10)
                pygame.draw.rect(display_surface, WHITE if can_buy else GRAY, rect, 2, 10)
                draw_text(display_surface, items[i][0], WHITE if can_buy else GRAY, rect.x + 15, rect.y + 10, font)
                draw_text(display_surface, items[i][1], GRAY, rect.x + 15, rect.y + 38, small_font)
            draw_text(display_surface, "[S] PALAA", CYAN, SCREEN_WIDTH//2, 650, font, True)

        elif game_state == "GAMEOVER":
            draw_text(display_surface, "ALUS TUHOUTUI TAI POLTTOAINE LOPPUI", RED, SCREEN_WIDTH//2, 350, font, True)
            draw_text(display_surface, "SPACE ALOITTAA ALUSTA", GOLD, SCREEN_WIDTH//2, 450, font, True)
            draw_text(display_surface, "ESC VALIKKOON", WHITE, SCREEN_WIDTH//2, 520, small_font, True)

        screen.blit(display_surface, off)
        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())