""" An Eittris (tetris) clone

mail: viblo@citro.se
"""

import os
from random import *

import pygame
from configobj import ConfigObj
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from pygame.locals import *

from blockfield import *
from blocks import *
from eit_constants import *


def glutBitmapCharacter(*args):
    pass

class PlayerField:
    """Player class. Holds info about a player."""

    def __init__(self, dm, id, name, px, py):

        self.dm = dm

        self.field = BlockField(dm, px, py)

        self.px = px
        self.py = py
        self.score = 0
        self.level = 0
        self.lines = 0

        self.id = id
        self.name = name
        self.target = None

        self.gameover = False
        self.to_nextlevel = TO_NEXT_LEVEL

        ### Special effects handling
        self.lines_to_add = []
        self.specialtime = 0
        self.rumbles = 0
        self.rumbleblocks = []
        self.packettime = 0
        self.antidotes = 0
        self.spawntime = SPAWN_SPECIAL_TIME - 4 * 1000

        ### FPS Safe block movement
        self.cstime = 0
        self.droptime = 0
        self.dropping = False
        self.cleared_lines = 0
        self.downtime = DOWN_TIME
        self.droptime = DROP_TIME

        self.load_controls()

    def load_controls(self):
        profiles = ConfigObj("profiles.cfg")
        if self.name in profiles:
            self.left = int(profiles[self.name]["Left"])
            self.right = int(profiles[self.name]["Right"])
            self.cw = int(profiles[self.name]["CW"])
            self.ccw = int(profiles[self.name]["CCW"])
            self.down = int(profiles[self.name]["Down"])
            self.drop = int(profiles[self.name]["Drop"])
            self.use_anti = int(profiles[self.name]["Anti"])
            self.change_target = int(profiles[self.name]["Change"])
        else:
            self.default_controls()

    def default_controls(self):
        """Default keys"""
        if self.id == 0:
            self.left = K_a
            self.right = K_d
            self.cw = K_q
            self.ccw = K_w
            self.down = K_s
            self.drop = K_LCTRL
            self.use_anti = K_LSHIFT
            self.change_target = K_TAB
        elif self.id == 1:
            self.left = K_LEFT
            self.right = K_RIGHT
            self.cw = K_6
            self.ccw = K_UP
            self.down = K_DOWN
            self.drop = K_SPACE
            self.use_anti = K_RSHIFT
            self.change_target = K_RETURN
        elif self.id == 2:
            self.left = K_LEFT
            self.right = K_RIGHT
            self.cw = K_6
            self.ccw = K_UP
            self.down = K_DOWN
            self.drop = K_SPACE
            self.use_anti = K_RSHIFT
            self.change_target = K_RETURN
        elif self.id == 3:
            self.left = K_KP2
            self.right = K_KP8
            self.cw = K_KP_PERIOD
            self.ccw = K_KP0
            self.down = K_KP5
            self.drop = K_KP_ENTER
            self.use_anti = K_KP_DIVIDE
            self.change_target = K_KP_MULTIPLY

    def do_score(self, lines):

        self.lines += lines
        if lines == 1:
            self.score += (self.level + 1) * 40
        elif lines == 2:
            self.score += (self.level + 1) * 100
        elif lines == 3:
            self.score += (self.level + 1) * 300
        elif lines == 4:
            self.score += (self.level + 1) * 1200

        ### Spawn next special block quicker the more lines that are cleared.
        if self.field.special_block is None:
            self.spawntime += 200

        self.to_nextlevel -= lines
        if self.to_nextlevel <= 0:
            # level up!
            self.to_nextlevel += TO_NEXT_LEVEL
            self.level += 1
            self.downtime /= DOWN_TIME_DELTA
            print("level up, new downtime is", self.downtime)

    def get_rumbleblocks(self):
        rumbleblocks = []
        for y in range(1, 23):
            for x in range(10):
                if self.field.blockparts[y][x] is not None:
                    rumbleblocks.append(self.field.blockparts[y][x])
                if len(rumbleblocks) > 5:
                    return rumbleblocks
        return rumbleblocks
        # sample( self.target.field.blockparts_list,
        # 							min( len(self.target.field.blockparts_list), 10 ) )

    def activate_special(self, special_block):
        if special_block is not None:
            if special_block.type == "Faster":
                self.dm.specialsounds["Faster"].play()
                if self.target is not None:
                    self.target.downtime = self.target.downtime * 0.75

            elif special_block.type == "Slower":
                self.dm.specialsounds["Slower"].play()
                self.downtime += 10.0 * DOWN_TIME_DELTA

            elif special_block.type == "Stair":
                if self.target is not None:
                    bp = choice(STANDARD_PARTS)(self.dm)
                    self.target.lines_to_add.append((22, [(0, bp), (1, None)]))

                    for x in range(1, 9):
                        bp = choice(STANDARD_PARTS)(self.dm)
                        self.target.lines_to_add.append(
                            (22 - x, [(x - 1, None), (x, bp), (x + 1, None)])
                        )

                    bp = choice(STANDARD_PARTS)(self.dm)
                    self.target.lines_to_add.append((13, [(8, None), (9, bp)]))
            elif special_block.type == "Fill":
                if self.target is not None:
                    for y in range(22, 12, -1):
                        bps = [None]
                        for i in range(9):
                            bps.append(choice(STANDARD_PARTS)(self.dm))
                        shuffle(bps)
                        line = []
                        for bp, x in zip(bps, range(10)):
                            line.append((x, bp))
                        self.target.lines_to_add.append((y, line))
            elif special_block.type == "Rumble":
                if self.target is not None:
                    self.target.rumbles = 5
                    self.target.rumbleblocks = self.target.get_rumbleblocks()
            elif special_block.type == "Inverse":
                self.dm.specialsounds["Inverse"].play()
                if self.target is not None:
                    self.target.field.effects["Inverse"] = BlockPartInverse(
                        self.target.dm, 0, 1
                    )
            elif special_block.type == "Switch":
                self.dm.specialsounds["Switch"].play()
                if self.target is not None:
                    self.field.blockparts, self.target.field.blockparts = (
                        self.target.field.blockparts,
                        self.field.blockparts,
                    )
                    self.field.blockparts_list, self.target.field.blockparts_list = (
                        self.target.field.blockparts_list,
                        self.field.blockparts_list,
                    )
                    self.field.special_block, self.target.field.special_block = (
                        self.target.field.special_block,
                        self.field.special_block,
                    )
                    self.rumbles = 0
                    self.rumbleblocks = []
                    self.target.rumbles = 0
                    self.target.rumbleblocks = []
            elif special_block.type == "Packet":
                self.packettime = PACKET_TIME
            elif special_block.type == "Flip":
                self.dm.specialsounds["Flip"].play()
                if self.target is not None:
                    self.target.field.flip()
            elif special_block.type == "Mini":
                self.dm.specialsounds["Mini"].play()
                if self.target is not None:
                    self.target.field.effects["Mini"] = BlockPartMini(
                        self.target.dm, 1, 1
                    )
            elif special_block.type == "Blink":
                self.dm.specialsounds["Blink"].play()
                if self.target is not None:
                    self.target.field.effects["Blink"] = BlockPartBlink(
                        self.target.dm, 2, 1
                    )
            elif special_block.type == "Blind":
                self.dm.specialsounds["Blind"].play()
                if self.target is not None:
                    self.target.field.effects["Blind"] = BlockPartBlind(
                        self.target.dm, 3, 1
                    )
            elif special_block.type == "Background":
                self.dm.specialsounds["Background"].play()
                if self.target is not None:
                    self.target.field.background_tile = (
                        self.target.field.random_background()
                    )
            elif special_block.type == "Anti":
                self.antidotes += 1
                if self.antidotes > 4:
                    self.antidotes = 4
            elif special_block.type == "Bridge":
                self.dm.specialsounds["Bridge"].play()
                if self.target is not None:
                    self.target.field.add_line(top=True)
                    self.target.field.add_line(top=True)
            elif special_block.type == "Trans":
                self.dm.specialsounds["Trans"].play()
                if self.target is not None:
                    self.target.field.effects["Trans"] = BlockPartTrans(
                        self.target.dm, 4, 1
                    )
            elif special_block.type == "Clear":
                self.dm.specialsounds["Clear"].play()
                self.field.clear_field()
            elif special_block.type == "Question":
                self.dm.specialsounds["Question"].play()
                if self.target is not None:
                    l = len(self.target.field.blockparts_list)
                    bps = sample(self.target.field.blockparts_list, int(l * 0.5))
                    for bp in bps:
                        self.target.field.remove_bp((bp.x, bp.y))
            elif special_block.type == "SZ":
                self.dm.specialsounds["SZ"].play()
                if self.target is not None:
                    self.target.field.effects["SZ"] = BlockPartSZ(self.target.dm, 5, 1)
            elif special_block.type == "Color":
                self.dm.specialsounds["Color"].play()
                if self.target is not None:
                    self.target.field.effects["Color"] = BlockPartColor(
                        self.target.dm, 6, 1
                    )
            elif special_block.type == "Ring":
                if self.target is not None:
                    self.target.lines_to_add += self.ring()
            elif special_block.type == "Castle":
                if self.target is not None:
                    self.target.field.clear_field()
                    self.target.lines_to_add += self.castle()

    def castle(self):
        lines = []
        lines.append(
            (
                22,
                [
                    (2, BlockPartGrey(self.dm)),
                    (3, BlockPartGrey(self.dm)),
                    (4, BlockPartGrey(self.dm)),
                    (5, BlockPartGrey(self.dm)),
                    (6, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                ],
            )
        )

        lines.append(
            (
                21,
                [
                    (2, BlockPartGrey(self.dm)),
                    (3, BlockPartGrey(self.dm)),
                    (4, BlockPartGrey(self.dm)),
                    (6, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                ],
            )
        )
        lines.append(
            (
                20,
                [
                    (2, BlockPartGrey(self.dm)),
                    (3, BlockPartGrey(self.dm)),
                    (4, BlockPartGrey(self.dm)),
                    (6, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                ],
            )
        )

        lines.append(
            (
                19,
                [
                    (2, BlockPartGrey(self.dm)),
                    (4, BlockPartGrey(self.dm)),
                    (5, BlockPartGrey(self.dm)),
                    (6, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                ],
            )
        )
        lines.append(
            (
                18,
                [
                    (2, BlockPartGrey(self.dm)),
                    (4, BlockPartGrey(self.dm)),
                    (5, BlockPartGrey(self.dm)),
                    (6, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                ],
            )
        )

        lines.append(
            (
                17,
                [
                    (2, BlockPartGrey(self.dm)),
                    (3, BlockPartGrey(self.dm)),
                    (4, BlockPartGrey(self.dm)),
                    (5, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                ],
            )
        )
        lines.append(
            (
                16,
                [
                    (2, BlockPartGrey(self.dm)),
                    (3, BlockPartGrey(self.dm)),
                    (4, BlockPartGrey(self.dm)),
                    (5, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                ],
            )
        )

        lines.append(
            (
                15,
                [
                    (2, BlockPartGrey(self.dm)),
                    (3, BlockPartGrey(self.dm)),
                    (5, BlockPartGrey(self.dm)),
                    (6, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                ],
            )
        )
        lines.append(
            (
                14,
                [
                    (2, BlockPartGrey(self.dm)),
                    (3, BlockPartGrey(self.dm)),
                    (5, BlockPartGrey(self.dm)),
                    (6, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                ],
            )
        )

        lines.append(
            (
                13,
                [
                    (1, BlockPartGrey(self.dm)),
                    (2, BlockPartGrey(self.dm)),
                    (3, BlockPartGrey(self.dm)),
                    (4, BlockPartGrey(self.dm)),
                    (5, BlockPartGrey(self.dm)),
                    (6, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                    (8, BlockPartGrey(self.dm)),
                ],
            )
        )
        lines.append(
            (
                12,
                [
                    (1, BlockPartGrey(self.dm)),
                    (2, BlockPartGrey(self.dm)),
                    (3, BlockPartGrey(self.dm)),
                    (4, BlockPartGrey(self.dm)),
                    (5, BlockPartGrey(self.dm)),
                    (6, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                    (8, BlockPartGrey(self.dm)),
                ],
            )
        )
        lines.append(
            (
                11,
                [
                    (1, BlockPartGrey(self.dm)),
                    (2, BlockPartGrey(self.dm)),
                    (4, BlockPartGrey(self.dm)),
                    (5, BlockPartGrey(self.dm)),
                    (7, BlockPartGrey(self.dm)),
                    (8, BlockPartGrey(self.dm)),
                ],
            )
        )
        return lines

    def ring(self):
        lines = []
        lines.append((22, [(3, None), (4, None), (5, None), (6, None)]))
        lines.append(
            (
                21,
                [
                    (1, None),
                    (2, None),
                    (3, choice(STANDARD_PARTS)(self.dm)),
                    (4, choice(STANDARD_PARTS)(self.dm)),
                    (5, choice(STANDARD_PARTS)(self.dm)),
                    (6, choice(STANDARD_PARTS)(self.dm)),
                    (7, None),
                    (8, None),
                ],
            )
        )
        lines.append(
            (
                20,
                [
                    (0, None),
                    (1, choice(STANDARD_PARTS)(self.dm)),
                    (2, choice(STANDARD_PARTS)(self.dm)),
                    (3, None),
                    (4, None),
                    (5, None),
                    (6, None),
                    (7, choice(STANDARD_PARTS)(self.dm)),
                    (8, choice(STANDARD_PARTS)(self.dm)),
                    (9, None),
                ],
            )
        )
        lines.append(
            (
                19,
                [
                    (0, None),
                    (1, choice(STANDARD_PARTS)(self.dm)),
                    (2, None),
                    (7, None),
                    (8, choice(STANDARD_PARTS)(self.dm)),
                    (9, None),
                ],
            )
        )
        for y in range(18, 14, -1):
            lines.append(
                (
                    y,
                    [
                        (0, choice(STANDARD_PARTS)(self.dm)),
                        (1, None),
                        (8, None),
                        (9, choice(STANDARD_PARTS)(self.dm)),
                    ],
                )
            )
        lines.append(
            (
                14,
                [
                    (0, None),
                    (1, choice(STANDARD_PARTS)(self.dm)),
                    (2, None),
                    (7, None),
                    (8, choice(STANDARD_PARTS)(self.dm)),
                    (9, None),
                ],
            )
        )
        lines.append(
            (
                13,
                [
                    (0, None),
                    (1, choice(STANDARD_PARTS)(self.dm)),
                    (2, choice(STANDARD_PARTS)(self.dm)),
                    (3, None),
                    (4, None),
                    (5, None),
                    (6, None),
                    (7, choice(STANDARD_PARTS)(self.dm)),
                    (8, choice(STANDARD_PARTS)(self.dm)),
                    (9, None),
                ],
            )
        )
        lines.append(
            (
                12,
                [
                    (1, None),
                    (2, None),
                    (3, choice(STANDARD_PARTS)(self.dm)),
                    (4, choice(STANDARD_PARTS)(self.dm)),
                    (5, choice(STANDARD_PARTS)(self.dm)),
                    (6, choice(STANDARD_PARTS)(self.dm)),
                    (7, None),
                    (8, None),
                ],
            )
        )
        lines.append((11, [(3, None), (4, None), (5, None), (6, None)]))
        return lines

    def handle_specials(self):
        if self.lines_to_add != []:
            self.dm.specialsounds["Stair"].play()
            y, line = self.lines_to_add.pop(0)
            for x, bp in line:
                if bp is not None:
                    self.field.insert_bp((x, y), bp)
                else:
                    self.field.remove_bp((x, y))
        if self.rumbles > 0:
            self.dm.specialsounds["Rumble"].play()
            for rb in self.rumbleblocks:
                nx = rb.x + choice([-1, 0, 1])
                ny = rb.y + choice([-1, 0])
                if nx < 0 or nx > 9 or ny < 2 or ny > 22:
                    pass
                else:
                    if self.field.blockparts[ny][nx] is None:
                        self.field.blockparts[rb.y][rb.x] = None
                        self.field.blockparts[ny][nx] = rb
                        rb.x = nx
                        rb.y = ny
            self.rumbles -= 1
            try:
                if random() > 0.1:
                    self.rumbleblocks.pop()
            except IndexError:
                self.rumbles = 0

    def do_gameover(self):
        self.dm.gameoversound.play()
        pygame.event.post(pygame.event.Event(USEREVENT, utype="GameOver", player=self))
        # self.dm.gameover_players.append(self)
        self.gameover = True

    def move_block(self, dir):
        if self.field.currentblock is None:
            ok = self.field.add_block()
            if not ok:
                self.do_gameover()
            return False
        if dir == "Down":
            self.field.currentblock.move(0, 1)
            if not self.field.in_valid_position(self.field.currentblock):
                self.field.currentblock.move(0, -1)
                self.field.place_currentblock()
            else:
                return False
        elif dir == "Left":
            self.field.currentblock.move(-1, 0)
            if not self.field.in_valid_position(self.field.currentblock):
                self.field.currentblock.move(1, 0)
            else:
                return False
        elif dir == "Right":
            self.field.currentblock.move(1, 0)
            if not self.field.in_valid_position(self.field.currentblock):
                self.field.currentblock.move(-1, 0)
            else:
                return False
        return True

    def next_target(self):
        self.dm.players.sort(key=lambda x: x.id)
        ok_players = list(filter(lambda x: not x.gameover, self.dm.players))
        if self.target is not None and not self.target.gameover:
            i = ok_players.index(self.target)
        else:
            i = ok_players.index(self)
        self.target = (ok_players + [ok_players[0]])[i + 1]
        if self.target is self:
            self.target = None

    def update(self, events, frametime):

        if self.gameover:
            return
        if self.target is not None and self.target.gameover:
            self.next_target()
        self.cstime += frametime
        self.droptime += frametime
        self.specialtime += frametime
        self.spawntime += frametime
        if self.packettime > 0:
            self.packettime -= frametime

        for event in events:
            if event.type == KEYDOWN and event.key == self.down:
                self.move_block("Down")
            elif event.type == KEYDOWN and event.key == self.left:

                if self.field.effects["Inverse"] is not None:
                    self.move_block("Right")
                else:
                    self.move_block("Left")
            elif event.type == KEYDOWN and event.key == self.right:
                if self.field.effects["Inverse"] is not None:
                    self.move_block("Left")
                else:
                    self.move_block("Right")
            elif event.type == KEYDOWN and event.key == self.cw:
                if self.field.effects["Inverse"] is not None:
                    self.field.rotate_block("ccw")
                else:
                    self.field.rotate_block("cw")
            elif event.type == KEYDOWN and event.key == self.ccw:
                if self.field.effects["Inverse"] is not None:
                    self.field.rotate_block("cw")
                else:
                    self.field.rotate_block("ccw")
            elif event.type == KEYDOWN and event.key == self.drop:
                self.dropping = True
                self.droptime = 0
            elif event.type == KEYDOWN and event.key == self.use_anti:
                if self.antidotes > 0:
                    self.dm.specialsounds["Anti"].play()
                    for k, v in self.field.effects.iteritems():
                        self.field.effects[k] = None
                    self.antidotes -= 1
            elif event.type == KEYDOWN and event.key == self.change_target:
                self.next_target()
            elif event.type == KEYDOWN and event.key == K_y:
                self.field.spawn_special()

        ### FPS-safe block down
        while self.cstime > self.downtime and not self.dropping:
            self.move_block("Down")
            self.cstime -= self.downtime

            cleared_lines, special_block = self.field.remove_full_rows()
            self.activate_special(special_block)
            self.do_score(cleared_lines)
            if self.packettime > 0 and self.target is not None:
                for x in range(cleared_lines):
                    self.target.field.add_line(top=False)
                    self.dm.specialsounds["Packet"].play()
            if cleared_lines == 4 and self.target is not None:
                self.dm.specialsounds["Bridge"].play()
                self.target.field.add_line(top=True)
                self.target.field.add_line(top=True)

        if self.cstime < 0:
            self.cstime = 0

        ### FPS-safe block drop
        if self.dropping:
            while self.droptime > DROP_TIME:
                enddrop = self.move_block("Down")
                self.droptime -= DROP_TIME
                if enddrop:
                    cleared_lines, special_block = self.field.remove_full_rows()
                    self.activate_special(special_block)
                    self.dropping = False
                    self.droptime = 0
                    self.do_score(cleared_lines)
                    if self.packettime > 0 and self.target is not None:
                        for x in range(cleared_lines):
                            self.dm.specialsounds["Packet"].play()
                            self.target.field.add_line(top=False)
                    if cleared_lines == 4 and self.target is not None:
                        self.dm.specialsounds["Bridge"].play()
                        self.target.field.add_line(top=True)
                        self.target.field.add_line(top=True)

        if self.droptime < 0:
            self.droptime = 0

        if self.specialtime > SPECIAL_TIME:
            self.handle_specials()
            self.specialtime = 0
            self.field.blink += 1
            if self.field.blink > 5:
                self.field.blink = 0

        if self.specialtime < 0:
            self.specialtime = 0

        if self.spawntime > SPAWN_SPECIAL_TIME - REMOVE_SPECIAL_TIME:
            self.field.remove_special()
        if self.spawntime > SPAWN_SPECIAL_TIME:
            self.field.spawn_special()
            self.spawntime = 0

    def draw(self):
        if self.gameover:
            glColor(0.7, 0.7, 0.7)

        glBindTexture(GL_TEXTURE_2D, self.dm.textures["background_info"])
        glLoadIdentity()
        glTranslated(self.px, self.py + 536, 0.0)
        glBegin(GL_QUADS)
        glTexCoord2d(0.0, 1.0)
        glVertex2d(0.0, 0.0)
        glTexCoord2d(0.96875, 1.0)
        glVertex2d(248.0, 0.0)
        glTexCoord2d(0.96875, 1 - 0.78125)
        glVertex2d(248.0, 200.0)
        glTexCoord2d(0.0, 1 - 0.78125)
        glVertex2d(0.0, 200.0)
        glEnd()

        ### Display some text
        glLoadIdentity()
        ### Name
        glRasterPos2d(self.px + 10, self.py + 560)
        name_text = self.name
        for c in name_text:
            glutBitmapCharacter(GLUT_BITMAP_9_BY_15, ord(c))
        ### Target
        glRasterPos2d(self.px + 10, self.py + 595)
        if self.target is not None:
            name_text = "Target: " + self.target.name
        else:
            name_text = "Target: None"
        for c in name_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
        ### Score
        glRasterPos2d(self.px + 10, self.py + 630)
        for c in "Score: " + str(self.score):
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
        ### Level
        glRasterPos2d(self.px + 10, self.py + 650)
        for c in "Level: " + str(self.level):
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))

        ### Packets
        if self.packettime > 0:
            s = self.packettime * 1.0 / PACKET_TIME
            glBindTexture(GL_TEXTURE_2D, self.dm.textures["special"])
            for y in range(int(s * 4.0 + 0.99)):
                glLoadIdentity()
                glTranslated(self.px + 155, self.py + 677 - y * 24, 0.0)

                glBegin(GL_QUADS)
                glTexCoord2d(7 / 22.0 * 0.515625, 1.0)
                glVertex2d(-12.0, -12.0)
                glTexCoord2d(8 / 22.0 * 0.515625, 1.0)
                glVertex2d(12.0, -12.0)
                glTexCoord2d(8 / 22.0 * 0.515625, 0.25)
                glVertex2d(12.0, 12.0)
                glTexCoord2d(7 / 22.0 * 0.515625, 0.25)
                glVertex2d(-12.0, 12.0)
                glEnd()

        ### Antidotes
        for x in range(self.antidotes):
            glBindTexture(GL_TEXTURE_2D, self.dm.textures["special"])
            glLoadIdentity()
            glTranslated(self.px + 27 + 24 * x, self.py + 669, 0.0)
            glBegin(GL_QUADS)
            glTexCoord2d(13 / 22.0 * 0.515625, 1.0)
            glVertex2d(-12.0, 0.0)
            glTexCoord2d(14 / 22.0 * 0.515625, 1.0)
            glVertex2d(12.0, 0.0)
            glTexCoord2d(14 / 22.0 * 0.515625, 0.25)
            glVertex2d(12.0, 24 * 1.0)
            glTexCoord2d(13 / 22.0 * 0.515625, 0.25)
            glVertex2d(-12.0, 24 * 1.0)
            glEnd()
        self.field.draw()
        glColor(1, 1, 1)
