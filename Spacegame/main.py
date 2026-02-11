import pygame
import math
import random
import os
import asyncio
import socket
import json


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
PURPLE = (200, 50, 255)
GRAY = (100, 100, 100)
DARK_BLUE = (20, 30, 50)
NEBULA_COLORS = [(20, 10, 40), (10, 20, 40), (30, 10, 30)]

# POLKUJEN HALLINTA
base_path = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(base_path, "assets")

font = pygame.font.SysFont('Futura', 30)
small_font = pygame.font.SysFont('Futura', 22)
menu_font = pygame.font.SysFont('Futura', 70)

def load_image(name, fallback_color, size):
    path = os.path.join(assets_path, name)
    try:
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(img, size)
    except:
        pass
    
    surf = pygame.Surface(size, pygame.SRCALPHA)
    if "asema" in name: 
        pygame.draw.circle(surf, GREEN, (size[0]//2, size[1]//2), size[0]//2, 4)
    elif "meteoriitti" in name: 
        pygame.draw.circle(surf, (80, 80, 85), (size[0]//2, size[1]//2), size[0]//2)
    elif "romu" in name:
        pts = [(size[0]//2, 0), (size[0], size[1]//2), (size[0]//2, size[1]), (0, size[1]//2)]
        pygame.draw.polygon(surf, fallback_color, pts)
    elif "r_nappi" in name:
        pygame.draw.rect(surf, GRAY, [0, 0, size[0], size[1]], 0, 5)
        r_txt = small_font.render("R", True, WHITE)
        surf.blit(r_txt, (size[0]//3, 5))
    else: 
        pygame.draw.rect(surf, fallback_color, [0, 0, size[0], size[1]])
    return surf

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, angle):
        super().__init__()
        self.image = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(self.image, CYAN, (5, 5), 5)
        self.rect = self.image.get_rect(center=pos)
        direction = pygame.math.Vector2(0, -1).rotate(-angle)
        self.vel = direction * 10
        self.life = 60

    def update(self):
        self.rect.center += self.vel
        self.life -= 1
        if self.life <= 0:
            self.kill()

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.original_image = load_image("pelaaja.png", CYAN, (45, 45))
        self.image = self.original_image
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
        self.vel = pygame.math.Vector2(0, 0)
        self.angle = 0
        self.attached_junks = []
        self.fuel = 100.0
        self.max_fuel = 100.0
        self.engine_power = 0.16
        self.rope_length = 45 
        self.shield = False
        self.has_weapon = False
        self.shoot_cooldown = 0
    def draw_nearest_indicator(self, surf, junk_group):
            closest_junk = None
            min_dist = 9999
            
            # Etsitään lähin vapaa romu
            for junk in junk_group:
                if not junk.attached:
                    dist = self.pos.distance_to(junk.pos)
                    if dist < min_dist:
                        min_dist = dist
                        closest_junk = junk
            
            # Piirretään pallo, jos romua löytyi
            if closest_junk:
                # Lasketaan suunta romuun
                direction = (closest_junk.pos - self.pos).normalize()
                # Pallo 50 pikselin päähän aluksesta
                indicator_pos = self.pos + direction * 50
                
                # Piirretään musta reunus ja värillinen pallo
                pygame.draw.circle(surf, (0, 0, 0), (int(indicator_pos.x), int(indicator_pos.y)), 7)
                pygame.draw.circle(surf, closest_junk.color, (int(indicator_pos.x), int(indicator_pos.y)), 5)
    def update(self, particles):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]: self.angle += 4.5
        if keys[pygame.K_d]: self.angle -= 4.5
        if keys[pygame.K_w] and self.fuel > 0:
            direction = pygame.math.Vector2(0, -1).rotate(-self.angle)
            thrust = self.engine_power
            for junk in self.attached_junks:
                thrust *= junk.weight
            self.vel += direction * thrust
            self.fuel -= 0.12 
            ex_pos = self.pos + pygame.math.Vector2(0, 18).rotate(-self.angle)
            particles.append({"pos": list(ex_pos), "vel": [-direction.x*2, -direction.y*2], "size": random.randint(4, 7), "color": list(ORANGE), "life": 1.0})
        
        if keys[pygame.K_s]: self.vel *= 0.94
        else: self.vel *= 0.982 

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        self.pos += self.vel
        self.pos.x %= SCREEN_WIDTH
        self.pos.y %= SCREEN_HEIGHT
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=(self.pos.x, self.pos.y))

class LaserShip(Player):
    def __init__(self, old_player):
        super().__init__()
        self.pos = old_player.pos
        self.vel = old_player.vel
        self.angle = old_player.angle
        self.fuel = old_player.fuel
        self.max_fuel = old_player.max_fuel
        self.engine_power = old_player.engine_power
        self.rope_length = old_player.rope_length
        self.attached_junks = old_player.attached_junks
        self.shield = old_player.shield
        self.has_weapon = True
        self.original_image = load_image("laser_ship.png", PURPLE, (50, 50))
        self.image = self.original_image

class MagneticShip(Player):
    def __init__(self, old_player):
        super().__init__()
        self.pos = old_player.pos
        self.vel = old_player.vel
        self.angle = old_player.angle
        self.fuel = old_player.fuel
        self.max_fuel = old_player.max_fuel
        self.engine_power = old_player.engine_power
        self.rope_length = old_player.rope_length
        self.attached_junks = old_player.attached_junks
        self.shield = old_player.shield
        self.has_weapon = old_player.has_weapon
        
        # Magneetin ominaisuudet - nostettu voimakkuutta
        self.magnetic_range = 250
        self.magnetic_strength = 2.5 # Nostettu huomattavasti
        self.original_image = load_image("magnetic_ship.png", (0, 255, 255), (50, 50))
        self.image = self.original_image

    def update(self, particles):
        if self.fuel > 0:
            # Huojuva ohjaus
            self.angle += math.sin(pygame.time.get_ticks() * 0.01) * 1.2
            self.vel += pygame.math.Vector2(random.uniform(-0.04, 0.04), random.uniform(-0.04, 0.04))
        super().update(particles)

    def apply_magnetism(self, junk_group):
        for junk in junk_group:
            if not junk.attached:
                # Lasketaan etäisyys aluksen ja romun välillä
                dist = self.pos.distance_to(junk.pos)
                if dist < self.magnetic_range:
                    # Lasketaan suuntavektori alusta kohti
                    pull_dir = (self.pos - junk.pos).normalize()
                    # Voima kasvaa mitä lähempänä romu on
                    pull_force = pull_dir * self.magnetic_strength * (1 - dist/self.magnetic_range)
                    
                    # Päivitetään sekä pos että rect, jotta peli piirtää ne oikein
                    junk.pos += pull_force
                    junk.rect.center = (junk.pos.x, junk.pos.y)

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
        self.rect.center = self.pos

    def update(self, target_pos, target_angle, rope_dist):
        if self.attached:
            target = target_pos + pygame.math.Vector2(0, rope_dist).rotate(-target_angle)
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

# --- 3. PÄÄFUNKTIO ---

async def main():
    score = 0
    high_score = 0
    game_state = "MENU"
    shake_amount = 0
    particles = []
    
    costs = [400, 600, 800, 300, 1500, 2000] # Lisätty magneettialuksen hinta
    fuel_boost = 40
    engine_boost = 0.05
    rope_boost = 25

    score_sound = nappaus_aani = rajahdys_aani = click_aani = shoot_aani = None
    try:
        if os.path.exists(assets_path):
            score_sound = pygame.mixer.Sound(os.path.join(assets_path, "score.wav"))
            nappaus_aani = pygame.mixer.Sound(os.path.join(assets_path, "nappaus.wav"))
            rajahdys_aani = pygame.mixer.Sound(os.path.join(assets_path, "rajahdys.wav"))
            click_aani = pygame.mixer.Sound(os.path.join(assets_path, "click.wav"))
            shoot_aani = pygame.mixer.Sound(os.path.join(assets_path, "shoot.wav"))

            
            music_file = os.path.join(assets_path, "music.wav")
            if os.path.exists(music_file):
                pygame.mixer.music.load(music_file)
                pygame.mixer.music.set_volume(0.4)
                pygame.mixer.music.play(-1)
    except Exception as e:
        print(f"Äänivirhe: {e}")

    def create_explosion(pos):
        for _ in range(60):
            particles.append({
                "pos": list(pos),
                "vel": [random.uniform(-7, 7), random.uniform(-7, 7)],
                "size": random.randint(5, 12),
                "color": list(random.choice([RED, ORANGE, GOLD])),
                "life": 2.0
            })
        if rajahdys_aani: rajahdys_aani.play()

    def start_new_game():
        nonlocal score, shake_amount, particles, player, station, junk_group, meteor_group, costs, fuel_boost, engine_boost, rope_boost, bullet_group
        player = Player()
        station = Station()
        junk_group = pygame.sprite.Group()
        meteor_group = pygame.sprite.Group()
        bullet_group = pygame.sprite.Group()
        particles = []
        score = 0
        shake_amount = 0
        costs = [400, 600, 800, 700, 1500, 2000]
        fuel_boost = 40
        engine_boost = 0.05
        rope_boost = 25
        for _ in range(8): junk_group.add(Junk(random.choice(["normal", "gold", "fuel", "radioactive"])))
        for _ in range(4): meteor_group.add(Meteor())
        return player, station, junk_group, meteor_group, bullet_group

    player, station, junk_group, meteor_group, bullet_group = start_new_game()
    stars = [[random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.uniform(0.5, 2.5)] for _ in range(180)]
    nebulae = [[random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.randint(150, 350), random.choice(NEBULA_COLORS)] for _ in range(6)]
    
    e_button_img = load_image("e_nappi.png", WHITE, (35, 35))
    r_button_img = load_image("r_nappi.png", WHITE, (40, 40)) 
    
    display_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    # Kaupan napit, lisätty kuudes paikka magneettialukselle
    shop_rects = [pygame.Rect(300, 220, 400, 60), pygame.Rect(300, 290, 400, 60), 
                    pygame.Rect(300, 360, 400, 60), pygame.Rect(300, 430, 400, 60),
                    pygame.Rect(300, 500, 400, 60), pygame.Rect(300, 570, 400, 60)]

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
            if event.type == pygame.QUIT: run = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: game_state = "MENU"
                if event.key == pygame.K_SPACE and game_state in ["MENU", "GAMEOVER"]:
                    player, station, junk_group, meteor_group, bullet_group = start_new_game()
                    game_state = "GAME"
                if event.key == pygame.K_r:
                    if game_state == "GAME" and player.rect.colliderect(station.rect.inflate(100, 100)):
                        if click_aani: click_aani.play()
                        game_state = "SHOP"
                    elif game_state == "SHOP":
                        if click_aani: click_aani.play()
                        game_state = "GAME"
            
            if event.type == pygame.MOUSEBUTTONDOWN and game_state == "SHOP":
                if shop_rects[0].collidepoint(mouse_pos) and score >= costs[0]:
                    if click_aani: click_aani.play()
                    score -= costs[0]; player.max_fuel += fuel_boost; player.fuel = player.max_fuel
                    costs[0] = int(costs[0] * 1.4); fuel_boost = int(fuel_boost * 1.3)
                elif shop_rects[1].collidepoint(mouse_pos) and score >= costs[1]:
                    if click_aani: click_aani.play()
                    score -= costs[1]; player.engine_power += engine_boost
                    costs[1] = int(costs[1] * 1.4); engine_boost *= 1.3
                elif shop_rects[2].collidepoint(mouse_pos) and score >= costs[2] and not player.shield:
                    if click_aani: click_aani.play()
                    score -= costs[2]; player.shield = True; costs[2] = int(costs[2] * 1.4)
                elif shop_rects[3].collidepoint(mouse_pos) and score >= costs[3]:
                    if click_aani: click_aani.play()
                    score -= costs[3]; player.rope_length += rope_boost
                    costs[3] = int(costs[3] * 1.4); rope_boost = int(rope_boost * 1.2)
                elif shop_rects[4].collidepoint(mouse_pos) and score >= costs[4] and not isinstance(player, LaserShip):
                    if click_aani: click_aani.play()
                    score -= costs[4]
                    player = LaserShip(player)
                elif shop_rects[5].collidepoint(mouse_pos) and score >= costs[5] and not isinstance(player, MagneticShip):
                    if click_aani: click_aani.play()
                    score -= costs[5]
                    player = MagneticShip(player)

        for p in particles[:]:
            p["pos"][0] += p["vel"][0]
            p["pos"][1] += p["vel"][1]
            p["vel"][0] *= 0.96
            p["vel"][1] *= 0.96
            p["life"] -= 0.02 
            
            if p["life"] <= 0:
                particles.remove(p)
            else:
                r = max(0, min(255, int(p["color"][0])))
                g = max(0, min(255, int(p["color"][1] * max(0, p["life"]))))
                b = max(0, min(255, int(p["color"][2])))
                size = int(p["size"] * max(0, p["life"]) * 2)
                if size > 0:
                    pygame.draw.circle(display_surface, (r, g, b), (int(p["pos"][0]), int(p["pos"][1])), size)
        
        if game_state == "MENU":
                    draw_text(display_surface, "AVARUUDEN ROMUNKERÄÄJÄ", CYAN, SCREEN_WIDTH//2, 150, menu_font, True)
                    y_offset = 280
                    ohjeet = [
                        "OHJEET:",
                        "W = Kaasu",
                        "A / D = Käännä alusta",
                        "S = Jarru",
                        "E = Poimi romua (lähellä romua)",
                        "R = Avaa kauppa (aseman lähellä)",
                        "SPACE = Ammu (kun ase on ostettu)",
                        "",
                        "Vie romut asemalle saadaksesi pisteitä!",
                        "Osta romuilla saaduista pisteistä kaupasta asioita",
                        "Varo meteoriitteja ja polttoaineen loppumista."
                    ]
                    for rivi in ohjeet:
                        vari = WHITE if "OHJEET" not in rivi else GOLD
                        draw_text(display_surface, rivi, vari, SCREEN_WIDTH//2, y_offset, small_font, True)
                        y_offset += 30
                    draw_text(display_surface, "Paina SPACE aloittaaksesi", GREEN, SCREEN_WIDTH//2, 600, font, True)
                    draw_text(display_surface, f"ENNÄTYS: {high_score}", GOLD, SCREEN_WIDTH//2, 660, font, True)
                
        elif game_state == "GAME":
            player.update(particles)
            if isinstance(player, MagneticShip):
                player.apply_magnetism(junk_group)
            player.draw_nearest_indicator(display_surface, junk_group)

                    # Pidetään magneettialuksen oma imutoiminto ennallaan:
            if isinstance(player, MagneticShip):
                player.apply_magnetism(junk_group)
            if player.has_weapon and pygame.key.get_pressed()[pygame.K_SPACE] and player.shoot_cooldown == 0:
                bullet_group.add(Bullet(player.pos, player.angle))
                player.shoot_cooldown = 20
                if shoot_aani: shoot_aani.play()

            bullet_group.update()
            
            for bullet in bullet_group:
                hit_meteors = pygame.sprite.spritecollide(bullet, meteor_group, False)
                for m in hit_meteors:
                    create_explosion(m.pos)
                    m.reset()
                    bullet.kill()
                    score += 50

            prev_pos, prev_angle = player.pos, player.angle
            for junk in player.attached_junks:
                junk.update(prev_pos, prev_angle, 40)
                prev_pos, prev_angle = junk.pos, 0
            
            meteor_group.update()

            if player.rect.colliderect(station.rect.inflate(100, 100)):
                display_surface.blit(r_button_img, (station.rect.centerx - 20, station.rect.bottom - 20))

            max_capacity = int(player.rope_length / 25)
            hits = pygame.sprite.spritecollide(player, junk_group, False)
            
            if len(player.attached_junks) < max_capacity and hits:
                target_junk = hits[0]
                if not target_junk.attached:
                    display_surface.blit(e_button_img, (target_junk.rect.centerx-17, target_junk.rect.top-35))
                    if pygame.key.get_pressed()[pygame.K_e]: 
                        target_junk.attached = True
                        player.attached_junks.append(target_junk)
                        if nappaus_aani: nappaus_aani.play()

            if pygame.sprite.spritecollide(player, meteor_group, False, pygame.sprite.collide_circle_ratio(0.7)):
                if player.shield: 
                    player.shield = False; shake_amount = 20
                    for m in meteor_group: m.reset()
                else:
                    create_explosion(player.pos)
                    if score > high_score: high_score = score
                    shake_amount = 40
                    game_state = "GAMEOVER"
            
            if player.fuel <= 0:
                create_explosion(player.pos)
                if score > high_score: high_score = score
                shake_amount = 40
                game_state = "GAMEOVER"

            display_surface.blit(station.image, station.rect)
            junk_group.draw(display_surface)
            meteor_group.draw(display_surface)
            bullet_group.draw(display_surface)
            
            current_start = player.pos
            for junk in player.attached_junks:
                pygame.draw.line(display_surface, (150, 150, 150), current_start, junk.pos, 2)
                current_start = junk.pos

            display_surface.blit(player.image, player.rect)
            if player.shield: pygame.draw.circle(display_surface, CYAN, player.pos, 35, 2)
            
            if player.attached_junks:
                for junk in player.attached_junks[:]:
                    if junk.rect.colliderect(station.rect):
                        score += junk.points
                        if score_sound: score_sound.play()
                        player.fuel = player.max_fuel if junk.jtype == "fuel" else min(player.max_fuel, player.fuel + 30)
                        junk.spawn_random()
                        player.attached_junks.remove(junk)

            draw_text(display_surface, f"PISTEET: {score}", WHITE, 25, 25, font)
            draw_text(display_surface, "POLTTOAINE", WHITE, 25, 65, small_font)
            pygame.draw.rect(display_surface, GREEN if player.fuel > 25 else RED, [130, 68, int(player.fuel/player.max_fuel*150), 12])
            draw_text(display_surface, f"KETJU: {len(player.attached_junks)}/{max_capacity}", GOLD, 25, 100, small_font)

        elif game_state == "SHOP":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 15, 25, 220)) 
            display_surface.blit(overlay, (0,0))
            
            draw_text(display_surface, "ASEMAN KAUPPA", GREEN, SCREEN_WIDTH//2, 80, menu_font, True)
            draw_text(display_surface, f"PISTEET: {score}", GOLD, SCREEN_WIDTH//2, 160, font, True)
            
            item_labels = ["LISÄÄ POLTTOAINETTA", "MOOTTORIN TEHO", "SHIELD", "PIDEMPI NARU", "LASER-SHIP", "MAGNETIC-SHIP"]
            
            for i, rect in enumerate(shop_rects):
                is_hovered = rect.collidepoint(mouse_pos)
                if is_hovered:
                    btn_color = (40, 60, 90)
                    border_color = CYAN
                    text_color = WHITE
                else:
                    btn_color = (20, 30, 45)
                    border_color = DARK_BLUE
                    text_color = GRAY if score < costs[i] else WHITE

                if i == 4 and isinstance(player, LaserShip):
                    text_color = GREEN
                    label = "LASER-SHIP OSTETTU"
                elif i == 5 and isinstance(player, MagneticShip):
                    text_color = GREEN
                    label = "MAGNETIC-SHIP OSTETTU"
                else:
                    label = f"{item_labels[i]} ({costs[i]}p)"

                pygame.draw.rect(display_surface, btn_color, rect, 0, 10)
                pygame.draw.rect(display_surface, border_color, rect, 2, 10) 
                draw_text(display_surface, label, text_color, rect.x + 20, rect.y + 18, font)
                
            draw_text(display_surface, "[R] PALAA PELIIN", CYAN, SCREEN_WIDTH//2, 680, font, True)

        elif game_state == "GAMEOVER":
            draw_text(display_surface, "ALUS TUHOUTUI!", RED, SCREEN_WIDTH//2, 300, menu_font, True)
            draw_text(display_surface, f"LOPULLISET PISTEET: {score}", WHITE, SCREEN_WIDTH//2, 400, font, True)
            draw_text(display_surface, "SPACE ALOITTAA ALUSTA", GOLD, SCREEN_WIDTH//2, 500, font, True)

        screen.blit(display_surface, off)
        pygame.display.flip()
        await asyncio.sleep(0)
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())