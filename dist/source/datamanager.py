import pygame
from pygame.locals import *

from random import *
import os

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

class DataManager:
	def __init__(self):
		self.textures = []
		self.backgrounds = []
		self.players = []
		soundpath = "sounds" 
		self.placesound = pygame.mixer.Sound(os.path.join(soundpath, "DEEK.WAV"))
		self.gameoversound = pygame.mixer.Sound(os.path.join(soundpath, "RASPB.WAV"))
		self.welcomesound = pygame.mixer.Sound(os.path.join(soundpath, "WELCOME.WAV"))
		self.specialsounds = {"Faster":pygame.mixer.Sound(os.path.join(soundpath, "LASER.WAV")),
						"Slower":pygame.mixer.Sound(os.path.join(soundpath, "PONG.WAV")),
						"Stair":pygame.mixer.Sound(os.path.join(soundpath, "FLOOP.WAV")), #PLUK?
						"Fill":pygame.mixer.Sound(os.path.join(soundpath, "POP2.WAV")), #
						"Rumble":pygame.mixer.Sound(os.path.join(soundpath, "BOUNCE.WAV")), #DINKLE?
						"Inverse":pygame.mixer.Sound(os.path.join(soundpath, "VIBRABEL.WAV")),
						"Flip":pygame.mixer.Sound(os.path.join(soundpath, "BOOMOOH-1.WAV")),
						"Switch":pygame.mixer.Sound(os.path.join(soundpath, "ECHOFST1.WAV")), #
						"Packet":pygame.mixer.Sound(os.path.join(soundpath, "PLICK.WAV")),
						"Clear":pygame.mixer.Sound(os.path.join(soundpath, "WHOOSH1.WAV")),
						"Question":pygame.mixer.Sound(os.path.join(soundpath, "PLOP1.WAV")),
						"Bridge":pygame.mixer.Sound(os.path.join(soundpath, "BOTTLED.WAV")),
						"Mini":pygame.mixer.Sound(os.path.join(soundpath, "FUU.WAV")),
						"Color":pygame.mixer.Sound(os.path.join(soundpath, "SPACEBO.WAV")),
						"Trans":pygame.mixer.Sound(os.path.join(soundpath, "PINC.WAV")),
						"SZ":pygame.mixer.Sound(os.path.join(soundpath, "PLINK2.WAV")),
						"Anti":pygame.mixer.Sound(os.path.join(soundpath, "SIGH.WAV")),
						"Background":pygame.mixer.Sound(os.path.join(soundpath, "KLOUNK.WAV")),
						"Blind":pygame.mixer.Sound(os.path.join(soundpath, "TICK.WAV")),
						"Blink":pygame.mixer.Sound(os.path.join(soundpath, "ZING.WAV")),}
	
	def load_textures(self):
		names = os.listdir("images")
		texture_names = []
		for name in names:
			if name.endswith(".png") and name not in ["main_eit.png", "main_right.png"]:
				texture_names.append(name)
		texture_ids = glGenTextures(len(texture_names))
		textures = {}
		for name, id in zip(texture_names, texture_ids):
			texturefile = os.path.join('images', name)
			texture_surface = pygame.image.load(texturefile)
			texture_data = pygame.image.tostring(texture_surface, "RGBX", 1)
			glBindTexture(GL_TEXTURE_2D, id)
			glTexImage2D( GL_TEXTURE_2D, 0, GL_RGBA, texture_surface.get_width(), texture_surface.get_height(), 0,
				  GL_RGBA, GL_UNSIGNED_BYTE, texture_data )
			glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
			glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
			textures[name[:-4]] = id  # we dont want the extension in the lookup dictionary
		
		self.textures = textures		
	
	def load_backgrounds(self, start_id):
		dir = os.path.join("images", "backgrounds")
		names = os.listdir( dir )
		texture_names = []
		for name in names:
			if name.endswith(".png"):
				texture_names.append(name)
		texture_ids = glGenTextures(len(texture_names))
		backgrounds = {}
		for name, id in zip(texture_names, texture_ids):
			try:
				texturefile = os.path.join(dir, name)
				texture_surface = pygame.image.load(texturefile)
				texture_data = pygame.image.tostring(texture_surface, "RGBX", 1)
				glBindTexture(GL_TEXTURE_2D, id)
				w = texture_surface.get_width()
				h = texture_surface.get_height()
				glTexImage2D( GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0,
					  GL_RGBA, GL_UNSIGNED_BYTE, texture_data )
				glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
				glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
				backgrounds[name[:-4]] = id  # we dont want the extension in the lookup dictionary
			except:
				pass
		self.backgrounds = backgrounds
		
	def random_music(self):
		try:
			filenames = os.listdir("music")
			fn = choice(filenames)
			print "music:", fn
			music = pygame.mixer.music.load("music/" + fn)
		except:
			print "Couldnt load " + fn