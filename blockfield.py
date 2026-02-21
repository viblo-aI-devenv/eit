""" An Eittris (tetris) clone

mail: viblo@citro.se
"""

import os
from random import *

from configobj import ConfigObj
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from pygame.locals import *

from blocks import *
from eit_constants import *


class BlockField:
    def __init__(self, dm, px, py):
        """px and py in screen coords of top left corner"""
        self.dm = dm

        self.background_tile = self.random_background()

        self.px = px + 4  # 4 is the n. of extra pixels from the border
        self.py = py + 4

        ### Field with block parts
        self.blockparts = []
        for y in range(23):
            self.blockparts.append([])
            for x in range(10):
                self.blockparts[-1].append(None)

        ### List of all block parts
        self.blockparts_list = []

        ### Special block
        self.special_block = None

        ### Special Effects
        self.effects = {
            "Inverse": None,
            "Mini": None,
            "Blink": None,
            "Blind": None,
            "Trans": None,
            "SZ": None,
            "Color": None,
        }
        self.blink = 0

        # Current "free" block
        self.currentblock = None
        self.nextblock = None

    def flip(self):
        top = self.top_index() + 1
        middle = top + (22 - top) / 2
        for y1, y2 in zip(range(top, middle + 1), range(22, middle - 1, -1)):
            for x in range(10):
                self.blockparts[y1][x], self.blockparts[y2][x] = (
                    self.blockparts[y2][x],
                    self.blockparts[y1][x],
                )
                if self.blockparts[y1][x] is not None:
                    self.blockparts[y1][x].y = y1
                if self.blockparts[y2][x] is not None:
                    self.blockparts[y2][x].y = y2

    def insert_bp(self, xy, bp):
        (x, y) = xy
        self.remove_bp((x, y))
        bp.x = x
        bp.y = y
        self.blockparts_list.append(bp)
        self.blockparts[y][x] = bp

    def remove_bp(self, xy):
        (x, y) = xy
        oldbp = self.blockparts[y][x]
        if oldbp is not None:
            if oldbp is self.special_block:
                self.special_block = None
            self.blockparts_list.remove(oldbp)
        self.blockparts[y][x] = None

    def replace_bp(self, oldbp, newbp):
        self.insert_bp((oldbp.x, oldbp.y), newbp)

    def spawn_special(self):
        if self.blockparts_list == []:
            return
        self.remove_special()
        oldbp = choice(self.blockparts_list)
        bp = choice(SPECIAL_PARTS + [BlockPartAnti] * EXTRA_ANTIS)(self.dm)
        self.replace_bp(oldbp, bp)
        self.special_block = bp

    def remove_special(self):
        oldbp = self.special_block
        if oldbp is None:
            return
        bp = choice(STANDARD_PARTS)(self.dm)
        self.replace_bp(oldbp, bp)
        self.special_block = None

    def inverse_dir(self, dir):
        if dir == "cw":
            return "ccw"
        else:
            return "cw"

    def rotate_block(self, dir="cw"):
        if self.currentblock is None:
            return
        # Check if it is possible to rotate
        self.currentblock.rotate(dir)
        if not self.in_valid_position(self.currentblock):
            self.currentblock.rotate(self.inverse_dir(dir))

    def add_bp(self, bp):
        """add blockpart bp to the playing field"""
        self.remove_bp((bp.x, bp.y))
        self.blockparts[bp.y][bp.x] = bp
        self.blockparts_list.append(bp)

    def add_block(self):
        x = choice([3, 4, 5, 6])  # randomly place block in x
        y = 0
        if self.nextblock is None:
            self.nextblock = self.random_block()(self.dm, 0, 1)
            self.currentblock = self.nextblock.__class__(self.dm, x, y)
        else:
            self.currentblock = self.nextblock.__class__(self.dm, x, y)
            self.nextblock = self.random_block()(self.dm, 0, 1)
        if self.nextblock.__class__ == BlockT:
            self.nextblock.rotate("ccw")
            self.nextblock.move(-1, 0)
        elif self.nextblock.__class__ == BlockO:
            self.nextblock.move(0, 1)
        return self.in_valid_position(self.currentblock)

    def random_block(self):
        if self.effects["SZ"] is not None:
            blocks = [BlockS, BlockZ]
        else:
            blocks = [BlockI, BlockT, BlockO, BlockL, BlockJ, BlockS, BlockZ]
        return choice(blocks)

    def random_background(self):
        background = choice(list(self.dm.backgrounds.values()))
        return background

    def clear_field(self):
        ### Field with block parts
        self.blockparts = []
        for y in range(23):
            self.blockparts.append([])
            for x in range(10):
                self.blockparts[-1].append(None)
        self.blockparts_list = []
        self.special_block = None

    def draw(self):

        glBindTexture(GL_TEXTURE_2D, self.dm.textures["background_border"])
        glLoadIdentity()
        glTranslated(self.px - 4, self.py - 4, 0.0)
        glBegin(GL_QUADS)
        glTexCoord2d(0.0, 1.0)
        glVertex2d(0.0, 0.0)
        glTexCoord2d(1.0, 1.0)
        glVertex2d(248.0, 0.0)
        glTexCoord2d(1.0, 0.0)
        glVertex2d(248.0, 536.0)
        glTexCoord2d(0.0, 0.0)
        glVertex2d(0.0, 536.0)
        glEnd()

        glBindTexture(GL_TEXTURE_2D, self.background_tile)
        glLoadIdentity()
        glTranslated(self.px, self.py, 0.0)
        glBegin(GL_QUADS)
        glTexCoord2d(0.0, 4.125)
        glVertex2d(0.0, 0.0)
        glTexCoord2d(1.875, 4.125)
        glVertex2d(240.0, 0.0)
        glTexCoord2d(1.875, 0.0)
        glVertex2d(240.0, 528.0)
        glTexCoord2d(0.0, 0.0)
        glVertex2d(0.0, 528.0)
        glEnd()

        glTranslated(0.0, -BLOCK_SIZE, 0.0)
        for bp in self.blockparts_list:
            if self.effects["Mini"] is not None:
                bp.draw(mini=True)
            elif self.effects["Trans"] is not None:
                bp.draw(trans=True)
            else:
                bp.draw()

        ### Color effect
        if self.effects["Color"] is not None:
            glLoadIdentity()
            glTranslated(self.px, self.py, 0.0)
            glBindTexture(GL_TEXTURE_2D, self.dm.textures["bw"])
            dx = 0
            dy = 0.25
            if self.currentblock is not None:
                dx = (self.currentblock.blockparts[0].x + 1) / (10.0 * 2) + 0.50
                dy = self.currentblock.blockparts[0].y / (22.0 * 2) + 0.50
                pass
            glBegin(GL_QUADS)
            glTexCoord2d(0.0 - dx, 0.0 - dy)
            glVertex2d(0.0, 0.0)
            glTexCoord2d(0.5 - dx, 0.0 - dy)
            glVertex2d(240.0, 0.0)
            glTexCoord2d(0.5 - dx, 0.5 - dy)
            glVertex2d(240.0, 528.0)
            glTexCoord2d(0.0 - dx, 0.5 - dy)
            glVertex2d(0.0, 528.0)
            glEnd()

        if self.currentblock is not None:
            if self.blink and self.effects["Blink"] is not None:
                pass
            else:
                glLoadIdentity()
                glTranslated(self.px, self.py - BLOCK_SIZE, 0.0)
                self.currentblock.draw()

        if self.nextblock is not None and self.effects["Blind"] is None:
            glLoadIdentity()
            glTranslated(self.px + 175, self.py + 567, 0.0)
            self.nextblock.draw()

        glLoadIdentity()
        glTranslated(self.px + 2, self.py + 677, 0.0)
        for _, sbp in self.effects.items():
            if sbp is not None:
                sbp.draw()

    def in_valid_position(self, block):
        """Check if the position of the blockparts in block is valid"""
        for bp in block.blockparts:
            try:
                if self.blockparts[bp.y][bp.x] is not None or bp.y < 0 or bp.x < 0:
                    return False
            except IndexError:
                return False
        return True

    def remove_full_rows(self):
        full_lines = []
        for line, i in zip(self.blockparts, range(len(self.blockparts))):
            full = True
            for bp in line:
                if bp is None:
                    full = False
            if full:
                full_lines.append(i)
        special_block = None
        for full_line in full_lines:
            tmp = self.remove_line(full_line)
            if tmp is not None:
                special_block = tmp
        return len(full_lines), special_block

    def remove_line(self, i):
        special_block = None
        for x in range(len(self.blockparts[i])):
            if self.blockparts[i][x].is_special:
                special_block = self.blockparts[i][x]
            self.remove_bp((x, i))

        for y in range(i - 1, 0 - 1, -1):
            for x in range(len(self.blockparts[y])):
                if self.blockparts[y][x] is not None:
                    self.move_bp(x, y, x, y + 1)
        return special_block

    def top_index(self):
        y = 22
        for bp in self.blockparts_list:
            if bp.y <= y:
                y = bp.y - 1
        # if y< 0: print "top_index(): y < 0"
        return max(y, 0)

    def add_line(self, top=True):
        if top:
            y = self.top_index()
            bps = [None]
            for x in range(9):
                bps.append(choice(STANDARD_PARTS)(self.dm))
            shuffle(bps)
            for bp, x in zip(bps, range(10)):
                if bp is not None:
                    self.insert_bp((x, y), bp)

        else:
            for y in range(1, 23):
                for x in range(len(self.blockparts[y])):
                    if self.blockparts[y][x] is not None:
                        self.move_bp(x, y, x, y - 1)
            bps = [None]
            for x in range(9):
                bps.append(choice(STANDARD_PARTS)(self.dm))
            shuffle(bps)
            for bp, x in zip(bps, range(10)):
                if bp is not None:
                    self.insert_bp((x, 22), bp)

    def move_bp(self, from_x, from_y, x, y):
        self.blockparts[y][x] = self.blockparts[from_y][from_x]
        self.blockparts[y][x].x = x
        self.blockparts[y][x].y = y
        self.blockparts[from_y][from_x] = None

    def place_currentblock(self):
        for bp in self.currentblock.blockparts:
            self.insert_bp((bp.x, bp.y), bp)
            # self.add_bp(bp)
        self.currentblock = None
        self.dm.placesound.play()

    def check(self):
        """Debug, check if blockparts and blockparts_list is in sync"""
        for bp in self.blockparts_list:
            try:
                if (
                    self.blockparts[bp.y][bp.x].x != bp.x
                    or self.blockparts[bp.y][bp.x].y != bp.y
                ):
                    print("check error 1", bp)
                    return False
            except IndexError:
                print("check error 2", bp.x, bp.y, self.blockparts[bp.y][bp.x])
                return False
        return True
