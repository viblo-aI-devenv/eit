from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

BLOCK_SIZE = 24
X,Y = 0,1	

class BlockPart:
	def __init__(self, x, y, texture):
		
		self.texture = texture
		self.w = BLOCK_SIZE
		self.h = BLOCK_SIZE
		
		# position in block coords
		self.x = x
		self.y = y
			
		self.tex_offset = (0,0)
		self.mini_offset = (0,0)
		self.is_special = False
		self.dl = None
		
	def create_dl(self, id):
		glNewList(id,GL_COMPILE)
		tex = self.tex_offset
		glBegin(GL_QUADS)
		glTexCoord2d( tex[0]*0.75, 1.0 ); glVertex2d(0.0, 0.0)
		glTexCoord2d( tex[1]*0.75, 1.0 ); glVertex2d(BLOCK_SIZE, 0.0)
		glTexCoord2d( tex[1]*0.75, 0.25 ); glVertex2d(BLOCK_SIZE, BLOCK_SIZE)
		glTexCoord2d( tex[0]*0.75, 0.25 ); glVertex2d(0.0, BLOCK_SIZE)
		glEnd()
		glEndList()
		self.dl = id

	def draw(self, mini = False, trans = False):
		if self.y == 0: # we dont want to draw blocks outside the field
			return
		glBindTexture(GL_TEXTURE_2D, self.texture)
		glPushMatrix()
		glTranslated(self.x * self.w, self.y * self.h, 0.0)
		if mini and self.__class__ is not BlockPartGrey:
			glScaled(0.4, 0.4, 1.0)
			glTranslated(self.mini_offset[X], self.mini_offset[Y], 0.0)
		tex = self.tex_offset
		if trans and self.__class__ is not BlockPartGrey:
			tex = (8 / 8.0, 9 / 8.0)
			glBegin(GL_QUADS)
			glTexCoord2d( tex[0]*0.75, 1.0 ); glVertex2d(0.0, 0.0)
			glTexCoord2d( tex[1]*0.75, 1.0 ); glVertex2d(BLOCK_SIZE, 0.0)
			glTexCoord2d( tex[1]*0.75, 0.25 ); glVertex2d(BLOCK_SIZE, BLOCK_SIZE)
			glTexCoord2d( tex[0]*0.75, 0.25 ); glVertex2d(0.0, BLOCK_SIZE)
			glEnd()
		elif self.dl is not None:
			glCallList(self.dl)
		else:
			glBegin(GL_QUADS)
			glTexCoord2d( tex[0]*0.75, 1.0 ); glVertex2d(0.0, 0.0)
			glTexCoord2d( tex[1]*0.75, 1.0 ); glVertex2d(BLOCK_SIZE, 0.0)
			glTexCoord2d( tex[1]*0.75, 0.25 ); glVertex2d(BLOCK_SIZE, BLOCK_SIZE)
			glTexCoord2d( tex[0]*0.75, 0.25 ); glVertex2d(0.0, BLOCK_SIZE)
			glEnd()
		
		glPopMatrix()
		
	def move(self, x, y):	
		self.x += x
		self.y += y

class BlockPartSpecial(BlockPart):
	def __init__(self, x, y, dm):
		BlockPart.__init__(self, x, y, dm.textures["special"])
		self.is_special = True
		self.type = None
	def draw(self, mini = False, trans = False):
		if self.y == 0: # we dont want to draw blocks outside the field
			return
		glBindTexture(GL_TEXTURE_2D, self.texture)
		glPushMatrix()
		glTranslated(self.x * self.w, self.y * self.h, 0.0)
		
		glBegin(GL_QUADS)
		glTexCoord2d( self.tex_offset[0]*0.515625, 1.0 ); glVertex2d(0.0, 0.0)
		glTexCoord2d( self.tex_offset[1]*0.515625, 1.0 ); glVertex2d(BLOCK_SIZE, 0.0)
		glTexCoord2d( self.tex_offset[1]*0.515625, 0.25 ); glVertex2d(BLOCK_SIZE, BLOCK_SIZE)
		glTexCoord2d( self.tex_offset[0]*0.515625, 0.25 ); glVertex2d(0.0, BLOCK_SIZE)
		glEnd()
		glPopMatrix()
#Special blockparts
class BlockPartFaster(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (0 / 22.0, 1 / 22.0)
		self.type = "Faster"
class BlockPartSlower(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (1 / 22.0, 2 / 22.0)
		self.type = "Slower"
class BlockPartStair(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (2 / 22.0, 3 / 22.0)
		self.type = "Stair"
class BlockPartFill(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (3 / 22.0, 4 / 22.0)
		self.type = "Fill"
class BlockPartRumble(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (4 / 22.0, 5 / 22.0)
		self.type = "Rumble"
class BlockPartInverse(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (5 / 22.0, 6 / 22.0)
		self.type = "Inverse"
class BlockPartSwitch(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (6 / 22.0, 7 / 22.0)
		self.type = "Switch"
class BlockPartPacket(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (7 / 22.0, 8 / 22.0)
		self.type = "Packet"
class BlockPartFlip(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (8 / 22.0, 9 / 22.0)
		self.type = "Flip"
class BlockPartMini(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (9 / 22.0, 10 / 22.0)
		self.type = "Mini"
class BlockPartBlink(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (10 / 22.0, 11 / 22.0)
		self.type = "Blink"
class BlockPartBlind(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (11 / 22.0, 12 / 22.0)
		self.type = "Blind"	
class BlockPartBackground(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (12 / 22.0, 13 / 22.0)
		self.type = "Background"
class BlockPartAnti(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (13 / 22.0, 14 / 22.0)
		self.type = "Anti"
class BlockPartBridge(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (14 / 22.0, 15 / 22.0)
		self.type = "Bridge"
class BlockPartTrans(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (15 / 22.0, 16 / 22.0)
		self.type = "Trans"
class BlockPartClear(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (16 / 22.0, 17 / 22.0)
		self.type = "Clear"
class BlockPartQuestion(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (17 / 22.0, 18 / 22.0)
		self.type = "Question"
class BlockPartSZ(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (18 / 22.0, 19 / 22.0)
		self.type = "SZ"
class BlockPartColor(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (19 / 22.0, 20 / 22.0)
		self.type = "Color"
class BlockPartRing(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (20 / 22.0, 21 / 22.0)
		self.type = "Ring"
class BlockPartCastle(BlockPartSpecial):
	def __init__(self, dm, x=0, y=0):
		BlockPartSpecial.__init__(self, x, y, dm)
		self.tex_offset = (21 / 22.0, 22 / 22.0)
		self.type = "Castle"
		
SPECIAL_PARTS = [BlockPartFaster, BlockPartSlower, BlockPartStair, BlockPartFill, 
				BlockPartRumble, BlockPartInverse, BlockPartSwitch, BlockPartPacket,
				BlockPartFlip, BlockPartMini, BlockPartBlink, BlockPartBlind, 
				BlockPartBackground, BlockPartAnti, BlockPartBridge, BlockPartTrans,
				BlockPartClear, BlockPartQuestion, BlockPartSZ, BlockPartColor,
				BlockPartRing, BlockPartCastle]

#SPECIAL_PARTS = [BlockPartRumble]

# Standard blockparts
class BlockPartRed(BlockPart):
	def __init__(self, dm, x=0, y=0):
		BlockPart.__init__(self, x, y, dm.textures["standard"])
		self.tex_offset = (1 / 8.0, 2 / 8.0)
		self.mini_offset = (32, 16)
		self.create_dl(1)
		
class BlockPartGreen(BlockPart):
	def __init__(self, dm, x=0, y=0):
		BlockPart.__init__(self, x, y, dm.textures["standard"])
		self.tex_offset = (2 / 8.0, 3 / 8.0)
		self.mini_offset = (16, 32)
		self.create_dl(2)
		
class BlockPartBlue(BlockPart):
	def __init__(self, dm, x=0, y=0):
		BlockPart.__init__(self, x, y, dm.textures["standard"])
		self.tex_offset = (0 / 8.0, 1 / 8.0)
		self.mini_offset = (32, 2)
		self.create_dl(3)
		
class BlockPartCyan(BlockPart):
	def __init__(self, dm, x=0, y=0):
		BlockPart.__init__(self, x, y, dm.textures["standard"])
		self.tex_offset = (5 / 8.0, 6 / 8.0)
		self.mini_offset = (32, 32)
		self.create_dl(4)
		
class BlockPartYellow(BlockPart):
	def __init__(self, dm, x=0, y=0):
		BlockPart.__init__(self, x, y, dm.textures["standard"])
		self.tex_offset = (3 / 8.0, 4 / 8.0)
		self.mini_offset = (2, 32)
		self.create_dl(5)
		
class BlockPartPurple(BlockPart):
	def __init__(self, dm, x=0, y=0):
		BlockPart.__init__(self, x, y, dm.textures["standard"])
		self.tex_offset = (4 / 8.0, 5 / 8.0)
		self.mini_offset = (0,0)
		self.create_dl(6)
		
class BlockPartGrey(BlockPart):
	def __init__(self, dm, x=0, y=0):
		BlockPart.__init__(self, x, y, dm.textures["standard"])
		self.tex_offset = (7 / 8.0, 8 / 8.0)
		self.create_dl(7)

class BlockPartPink(BlockPart):
	def __init__(self, dm, x=0, y=0):
		BlockPart.__init__(self, x, y, dm.textures["standard"])
		self.tex_offset = (6 / 8.0, 7 / 8.0)
		self.mini_offset = (16,16)
		self.create_dl(8)
		
STANDARD_PARTS = [BlockPartPink, BlockPartPurple, BlockPartYellow, 
				BlockPartCyan, BlockPartBlue, BlockPartGreen, BlockPartRed]	

#Blocks
class Block:
	""" Note that the first blockpart in a block specifies which block to rotate around """
	def __init__(self, dm):
		self.blockparts = []
		self.dm = dm
	def rotate(self, dir="cw"):
		# Rotate around the first blockpart
		bp = self.blockparts[0]
		x = bp.x
		y = bp.y
		for bp in self.blockparts[1:]:
			bp.x -= x 
			bp.y -= y
			ox = bp.x
			if dir == "cw":
				bp.x = bp.y * -1 
				bp.y = ox
			else:
				bp.x = bp.y
				bp.y = ox * -1
			bp.x += x
			bp.y += y
			
	def add(self, a,b,c,d):
		self.blockparts += [a,b,c,d]
		
	def move(self, x, y):
		for bp in self.blockparts:
			bp.move(x, y)
				
	def draw(self):
		for bp in self.blockparts:
			bp.draw()

class BlockO(Block):
	def __init__(self, dm, x, y):
		Block.__init__(self, dm)
		a = BlockPartPurple(dm, 0, 0)
		b = BlockPartPurple(dm, 1, 0)
		c = BlockPartPurple(dm, 0, 1)
		d = BlockPartPurple(dm, 1, 1)
		self.add(a, b, c, d)
		self.move(x, y)
	def rotate(self, dir="cw"):
		# O-blocks cannot rotate
		return
class BlockI(Block):
	def __init__(self, dm, x, y):
		Block.__init__(self, dm)
		b = BlockPartRed(dm, 0, 0)
		a = BlockPartRed(dm, 0, 1)
		c = BlockPartRed(dm, 0, 2)
		d = BlockPartRed(dm, 0, 3)
		self.add(a, b, c, d)
		self.move(x, y)
	def rotate(self, dir="cw"):
		# I-blocks only rotate half the time.
		### BUG; FIXME!
		Block.rotate(self, dir)
			
class BlockT(Block):
	def __init__(self, dm, x, y):
		Block.__init__(self, dm)
		b = BlockPartCyan(dm, 0, 1)
		a = BlockPartCyan(dm, 1, 1)
		c = BlockPartCyan(dm, 2, 1)
		d = BlockPartCyan(dm, 1, 2)
		self.add(a, b, c, d)
		self.move(x, y)

class BlockL(Block):
	def __init__(self, dm, x, y):
		Block.__init__(self, dm)
		b = BlockPartGreen(dm, 0, 0)
		a = BlockPartGreen(dm, 0, 1)
		c = BlockPartGreen(dm, 0, 2)
		d = BlockPartGreen(dm, 1, 2)
		self.add(a, b, c, d)
		self.move(x, y)

class BlockJ(Block):
	def __init__(self, dm, x, y):
		Block.__init__(self, dm)
		b = BlockPartBlue(dm, 1, 0)
		a = BlockPartBlue(dm, 1, 1)
		c = BlockPartBlue(dm, 0, 2)
		d = BlockPartBlue(dm, 1, 2)
		self.add(a, b, c, d)
		self.move(x, y)
		
class BlockS(Block):
	def __init__(self, dm, x, y):
		Block.__init__(self, dm)
		b = BlockPartPink(dm, 0, 0)
		a = BlockPartPink(dm, 0, 1)
		c = BlockPartPink(dm, 1, 1)
		d = BlockPartPink(dm, 1, 2)
		self.add(a, b, c, d)
		self.move(x, y)
			
class BlockZ(Block):
	def __init__(self, dm, x, y):
		Block.__init__(self, dm)
		b = BlockPartYellow(dm, 1, 0)
		a = BlockPartYellow(dm, 0, 1)
		c = BlockPartYellow(dm, 1, 1)
		d = BlockPartYellow(dm, 0, 2)
		self.add(a, b, c, d)
		self.move(x, y)

ALL_BLOCKS = [BlockI, BlockT, BlockO, BlockL, BlockJ, BlockS, BlockZ]
