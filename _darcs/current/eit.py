""" An Eittris (tetris) clone

mail: viblo@citro.se
"""
import psyco
psyco.full()

import pygame
from pygame.locals import *

from random import *
import os
import pickle 

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from blocks import *
from dialogs import *
from datamanager import *
from eit_constants import *
from playerfield import *

from pgu import gui

def resize((width, height)):
	if height==0:
		height=1
	glViewport(0, 0, width, height)
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	glOrtho(0.0, width, height, 0.0, -1.0, 1.0)
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()

def init():
	glEnable(GL_TEXTURE_2D)
	glShadeModel(GL_SMOOTH)
	glClearColor(0.0, 0.0, 0.0, 0.0)
	glClearDepth(1.0)
	#glEnable(GL_DEPTH_TEST)
	
	#glEnable(GL_ALPHA_TEST)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	glEnable(GL_BLEND)
	
	glDepthFunc(GL_LEQUAL)
	glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)

import operator
class Scoretable:
	def __init__(self):
		self.stats = {}
		"""
		self.stats = {"Test":{"Matches":0, "Score":0, "Lines":0, "Max Level":0, 
							  "Rank Points":0, "Winns":0}}
		"""
	def get_list(self):
		l = self.stats.items()
		l.sort(key=lambda x:x[1]["Rank Points"])
		l.reverse()
		print l
		return l
	def insert_result(self, winner, losers):
		### Update winner
		if not self.stats.has_key(winner["Name"]):
			self.stats[winner["Name"]] = {"Matches":0, "Score":0, "Lines":0, "Max Level":0, 
										  "Rank Points":0, "Winns":0}
			
		self.stats[winner["Name"]]["Matches"] += 1
		self.stats[winner["Name"]]["Score"] += winner["Score"]
		self.stats[winner["Name"]]["Lines"] += winner["Lines"]
		self.stats[winner["Name"]]["Max Level"] = max(winner["Level"], 
													   self.stats[winner["Name"]]["Max Level"])
		self.stats[winner["Name"]]["Winns"] += 1
		print "level"
		print winner["Level"]
		print self.stats[winner["Name"]]["Max Level"]
		### Update losers + rp for winner
		for stat in losers:
			if not self.stats.has_key(stat["Name"]):
				self.stats[stat["Name"]] = {"Matches":0, "Score":0, "Lines":0, "Max Level":0, 
										    "Rank Points":0, "Winns":0}
			self.stats[stat["Name"]]["Matches"] += 1
			self.stats[stat["Name"]]["Score"] += stat["Score"]
			self.stats[stat["Name"]]["Lines"] += stat["Lines"]
			self.stats[stat["Name"]]["Max Level"] = max(stat["Level"], 
														   self.stats[stat["Name"]]["Max Level"])
			w = self.stats[winner["Name"]]["Rank Points"]
			l = self.stats[stat["Name"]]["Rank Points"]
			### Calc new rank points
			if w > l + 5:
				rp = 5
			else:
				rp = (w - l) / 2 + 5
			self.stats[winner["Name"]]["Rank Points"] += rp
			self.stats[stat["Name"]]["Rank Points"] -= rp	
		
class Main(gui.Container):

	def load_scoretable(self):
		try:
			f = open("scoretable.dat", "r")
			self.scoretable = pickle.load(f)
		except:
			self.scoretable = Scoretable()
			self.save_scoretable()
		
	def save_scoretable(self):
		if self.scoretable is not None:
			f = open("scoretable.dat", "w")
			pickle.dump(self.scoretable, f)
			
	def __init__(self):
		
		self.all_gameover = False
		### Load scoretable
		self.load_scoretable()
		### Load settings
		settings = ConfigObj("settings.cfg")		
		self.active_profiles = {0:settings["0"], 1:settings["1"], 2:settings["2"], 3:settings["3"]}
		self.fullscreen = settings["Fullscreen"] == "True"
		self.music = settings["Music"] == "True"
		
		gui.Container.__init__(self,)
		width = 640
		height = 500
		textcolor = (0,255,0)
		
		doc = gui.Document(width=width)
		title = gui.Label("a") # UGLY HACK
		space = title.style.font.size(" ")
		
		### Background
		img = gui.Image(os.path.join("images", "main_right.png"))
		self.add(img, 340, 0)
		
		img = gui.Image(os.path.join("images", "main_eit.png"))
		self.add(img, 50, 48)
				
		### List of active profiles
		t = gui.Table(width = 200)
		self.add(t, 10, 300)
		
		t.tr()
		t.td(gui.Label("Active Profiles:", color=textcolor))
		t.tr()
		t.td(gui.Spacer(1,10))
		t.tr()
		
		t2 = gui.Table(width=210)
		
		self.active_profiles_buttons = (gui.Button(self.active_profiles[0], width=100), 
								gui.Button(self.active_profiles[1], width=100),
								gui.Button(self.active_profiles[2], width=100), 
								gui.Button(self.active_profiles[3], width=100))
		d = SelectProfileDialog()
		d.connect(gui.CHANGE,self.m_select_profile, d)
		for i in range(4):
			t2.tr()
			t2.td( gui.Label("P" + str(i+1) + ":", color=textcolor) )
			
			profile = self.active_profiles[i]
			e = self.active_profiles_buttons[i]
			e.connect(gui.CLICK, self.m_open, (d,i))
			t2.td( e )
			b = gui.Button("Clear", width=40)
			b.connect(gui.CLICK, self.m_del, i)
			t2.td(b)
		t.td(t2, aligh =0)
	
		
		### Start Game and other buttons
		t = gui.Table(width = 150)
		self.add(t, 250, 300)
		
		t.td(gui.Spacer(1,10))
		t.tr()
		b = gui.Button("Start Game", width=120)
		b.connect(gui.CLICK,self.m_start_game,None)
		t.td(b, align=0)
		
		t.tr()
		t.td(gui.Spacer(1,10))
		
		b = gui.Button("Highscores", width=120)
		d = ViewScoreDialog(self.scoretable)
		b.connect(gui.CLICK, d.open, None)
		t.tr()
		t.td(b, align=0)
			
		b = gui.Button("Edit Profiles", width=120)
		b.connect(gui.CLICK, self.m_manage_profiles, None)
		t.tr()
		t.td(b, align=0)
		
		b = gui.Button("Help", width=120)
		d = HelpDialog()
		b.connect(gui.CLICK, d.open, None)
		t.tr()
		t.td(b, align=0)
		
		
		
		t.tr()
		t.td(gui.Spacer(1,10))

		b = gui.Button("Quit", width=120)
		b.connect(gui.CLICK, self.m_quit_game, True)
		t.tr()
		t.td(b, align=0)
		
		t.tr()
		t.td(gui.Spacer(1,10))
		
		### Options
		t = gui.Table(width = 100)
		self.add(t, 20, 450)
		
		t.tr()
		t.td(gui.Label("Fullscreen: ", color=textcolor), align = 1)
		self.switch_fullscreen = gui.Switch(value = self.fullscreen)
		self.switch_fullscreen.connect(gui.CHANGE, self.m_fullscreen, None)
		t.td(self.switch_fullscreen, align = -1)
		
		t.tr()
		t.td(gui.Label("Music: ", color=textcolor), align = 1)
		self.switch_music = gui.Switch(value = self.music)
		self.switch_music.connect(gui.CHANGE, self.m_music, None)
		t.td(self.switch_music)
		
	
	def m_fullscreen(self, e):
		self.fullscreen = not self.fullscreen
		self.save_settings()
		
	def m_music(self, e):
		self.music = not self.music
		self.save_settings()
		
	def m_del(self, i):
		self.active_profiles_buttons[i].value = "None"
		self.active_profiles[i] = "None"
		self.save_settings()
		
	def m_open(self, (d,i)):
		d.open()
		self.i = i

	def m_manage_profiles(self, e):
		d = ManageProfilesDialog()
		d.open()
	
	def save_settings(self):
		settings = ConfigObj("settings.cfg")
		settings["0"] = self.active_profiles[0]
		settings["1"] = self.active_profiles[1]
		settings["2"] = self.active_profiles[2]
		settings["3"] = self.active_profiles[3]
		settings["Music"] = str(self.music)
		settings["Fullscreen"] = str(self.fullscreen)
		settings.write()
		
	def m_select_profile(self, d):
		name = d.profile_list.value
		d.close()
		self.active_profiles_buttons[self.i].value = name
		self.active_profiles[self.i] = name
		self.save_settings()
	
	def m_start_game(self, e):
		event = pygame.event.Event(KEYDOWN, {"key":K_F2})
		pygame.event.post(event)

	def m_quit_game(self, e):
		#self.app.quit()
		event = pygame.event.Event(QUIT)
		pygame.event.post(event)

	def init_menu(self):
		### Menu here:
		app = gui.App(theme=gui.Theme(dirs=[os.path.join("data", "themes", "eit")]))
		t = self
	
		c = gui.Container(align=-1,valign=-1)
		c.add(t,0,0)
		
		app.init(c)
		return app

	def init_game(self):
		resize((1024, 768))
		init()
		pygame.mouse.set_visible(False)
		#pygame.event.set_grab(1)
		self.dm = DataManager()
		self.dm.load_textures()
		self.dm.load_backgrounds()
		self.dm.music = self.music
		self.dm.fullscreen = self.fullscreen
		
		
	def start_new_game(self):
		""" Start a new game """
		### music
		if self.dm.music:
			self.dm.random_music()
			pygame.mixer.music.play(-1) # infinite loop of music
		
		### Players
		self.dm.players = []
		self.dm.gameover_players = []
		if self.active_profiles[0] != "None":
			player1field = PlayerField(self.dm, 0, self.active_profiles[0] , 0+16, 16)
			self.dm.players.append(player1field)
		if self.active_profiles[1] != "None":
			player2field = PlayerField(self.dm, 1, self.active_profiles[1], 248+16, 16)
			self.dm.players.append(player2field)
		if self.active_profiles[2] != "None":
			player3field = PlayerField(self.dm, 2, self.active_profiles[2], 248*2+16, 16)
			self.dm.players.append(player3field)
		if self.active_profiles[3] != "None":
			player4field = PlayerField(self.dm, 3, self.active_profiles[3], 248*3+16, 16)
			self.dm.players.append(player4field)

		for player in self.dm.players:
			player.next_target()
			
		self.all_gameover = False
		self.paused = False
		self.dm.welcomesound.play()
	
	def pause_screen(self):
		size = 1024, 768
		glLoadIdentity()
		glTranslated(size[X] / 2, size[Y] / 2, 0.0)
		glColor4d(0.2,0.2,0.2,0.5)
		glDisable(GL_TEXTURE_2D)
		glBegin(GL_QUADS)
		glVertex2d(-496, -100)
		glVertex2d(496, -100)
		glVertex2d(496, 100)
		glVertex2d(-496, 100)
		glEnd()
		glColor(1.0,1.0,1.0)
		glRasterPos2d(-75, 12)
		for c in "Game Paused":
			glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(c))
		glRasterPos2d(-75, 40)	
		for c in "(press Pause to unpause)":
			glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(c))	
		glEnable(GL_TEXTURE_2D)
		
	def gameover_screen(self):
		size = 1024, 768
		#size = 4*248, 735
		glLoadIdentity()
		glTranslated(size[X] / 2, size[Y] / 2, 0.0)
		glColor4d(0.2,0.2,0.2,0.5)
		glDisable(GL_TEXTURE_2D)
		glBegin(GL_QUADS)
		glVertex2d(-496, -100)
		glVertex2d(496, -100)
		glVertex2d(496, 100)
		glVertex2d(-496, 100)
		glEnd()
		glColor(1.0,1.0,1.0)
		glRasterPos2d(-75, 12)
		
		for c in "GAME OVER!":
			glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(c))
		glRasterPos2d(-90, 40)	
		for c in "(press F2 to restart, ESC to quit)":
			glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(c))
		glEnable(GL_TEXTURE_2D)
	
	def to_menu(self):
		self.screen = pygame.display.set_mode((640, 500), SWSURFACE)
		pygame.mouse.set_visible(True)
		self.state = "Menu"
	
	def calc_stats(self, winner):
		losers = []
		w = None
		for p in self.dm.players:
			stat= {"Name":p.name, "W": False, "Score":p.score, "Lines":p.lines, "Level":p.level}
			if p is winner:
				stat["W"] = True
				w = stat
			else:
				losers.append(stat)
		self.scoretable.insert_result(w, losers)
		self.save_scoretable()
		
	def loop(self):
		"""Main Loop"""
		if self.state == "Menu":
			self.screen.fill((255,255,255))
			self.screen.fill((0,0,0))
			self.app.paint(self.screen)
			for event in pygame.event.get():
				if event.type == QUIT:
					self.running = False
				elif event.type == KEYDOWN and event.key == K_ESCAPE:
					self.running = False
				elif event.type == KEYDOWN and event.key == K_F2:
					self.state = "Game"
					if self.fullscreen:
						self.screen = pygame.display.set_mode((1024, 768), OPENGL|DOUBLEBUF|FULLSCREEN)
					else:
						self.screen = pygame.display.set_mode((1024, 768), OPENGL|DOUBLEBUF)
					self.init_game()
					self.start_new_game()
				self.app.event(event)
			
			pygame.time.wait(6) ### Uncomment here and in menu to not use all cpu
			self.clock.tick(60)
			pygame.display.flip()
		
		elif self.state == "Paused":
			
			for event in pygame.event.get():
				if event.type == QUIT:
					self.running = False
				elif event.type == KEYDOWN and event.key == K_ESCAPE:
					self.to_menu()
				elif event.type == KEYDOWN and event.key == K_PAUSE:
					self.state = "Game"
				elif event.type == KEYDOWN and event.key == K_F2:
					self.start_new_game()	
			glClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT )
			for player in self.dm.players:
				player.draw()
			self.pause_screen()
			
			pygame.time.wait(6) ### Uncomment here and in menu to not use all cpu
			self.clock.tick(60)
			pygame.display.flip()
			
		elif self.state == "GameOver":
			for event in pygame.event.get():
				if event.type == QUIT:
					self.running = False
				elif event.type == KEYDOWN and event.key == K_ESCAPE:
					self.to_menu()
				elif event.type == KEYDOWN and event.key == K_F2:
					self.start_new_game()
					
			glClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT )
			for player in self.dm.players:
				player.draw()
				
			self.gameover_screen()
			pygame.time.wait(6) ### Uncomment here and in menu to not use all cpu
			self.clock.tick(60)
			pygame.display.flip()	
				
		elif self.state == "Game":
			self.fps_var += 1
			#pygame.time.wait(6) ### Uncomment here and in menu to not use all cpu
			
			frametime = self.clock.tick(150)
			
			player_events = []
			
			for event in pygame.event.get():
				if event.type == QUIT:
					self.running = False
				elif event.type == KEYDOWN and event.key == K_ESCAPE:
					self.to_menu()
				elif event.type == KEYDOWN and event.key == K_PAUSE:
					self.state = "Paused"
				elif event.type == KEYDOWN and event.key == K_F2:
					self.start_new_game()
				elif event.type == USEREVENT and event.utype == "GameOver":
					self.dm.gameover_players.append(event.player)
					if len(self.dm.gameover_players) == len(self.dm.players):
						print event.player.name + " is the winner!"
						self.state = "GameOver"
						self.calc_stats(event.player)
				else:
					player_events.append(event)
			
			glClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT )
				
			### let each player do its own event handling and drawing
			for player in self.dm.players:
				player.update(player_events, frametime)
				
			for player in self.dm.players:
				player.draw()
			
			fps = self.clock.get_fps()
			if self.fps_var > 50:
				fps = self.clock.get_fps()
				pygame.display.set_caption('Eit - fps: ' + str(fps)[:5] )
				self.fps_var = 0
		
			pygame.display.flip()
		
	def main(self):
	
		### Initialise screen
		pygame.init()
		self.screen = pygame.display.set_mode((640, 500), SWSURFACE)
		pygame.display.set_caption('Eit')
		
		self.app = self.init_menu()
		self.clock = pygame.time.Clock()
		
		### We want to receive multiple KEYDOWN events
		#pygame.key.set_repeat(130, 30)
		#pygame.key.set_repeat(130, 20)
		### We dont want to receive multiple KEYDOWN event
		pygame.key.set_repeat()
		
		### Event loop
		self.fps_var = 0
		self.running = True
		self.in_menu = True
		self.state = "Menu"
		while self.running:
			self.loop()

def run_game():
	m = Main()
	m.main()

def run_test():
	
	import profile
	import pstats

	profile.run( "run_game()", "benchmark.prof" )
	p = pstats.Stats( "benchmark.prof" )
	p.strip_dirs()
	p.sort_stats( 'time' )
	#p.sort_stats('cumulative')
	p.print_stats( 30 )
	#p.sort_stats('cumulative').print_stats(10)
	
	"""
	### profiling with hotshot 
	### a bit faster during runtime, a bit slower when calculating the result
	import hotshot, hotshot.stats
	prof = hotshot.Profile("stones.prof")
	prof.runcall(run_game)
	prof.close()
	stats = hotshot.stats.load("stones.prof")
	stats.strip_dirs()
	stats.sort_stats('cumulative', 'time', 'calls')
	stats.print_stats(30)
	"""

if __name__ == '__main__': 
	DO_PROFILING = 0
	if not DO_PROFILING:
		run_game()
	else:
		run_test()
	
	
	