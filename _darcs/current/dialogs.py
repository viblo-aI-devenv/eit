from pgu import gui
from pgu import high
from pygame.locals import *
import pygame
import os
from configobj import ConfigObj


class ManageProfilesDialog(gui.Dialog):
	def __init__(self):
		
		title = gui.Label("Manage Profiles")
		
		width = 500
		height = 300
		t = gui.Table(width=width, height = height, background = (0,0,0))
		
		space = (5,5) #title.style.font.size(" ")
		t.tr()
		txtcolor = (0,255,0)
		profiles = ConfigObj("profiles.cfg")
		
		
		### New Profile
		doc = gui.Document(width = 100, background = (0,0,0))
		t2 = gui.Table(width = 100, height = 100, background = (0,0,0))
		
		t2.tr()
		t2.td(gui.Label("Name: ", color = txtcolor), align=1)
		self.name = gui.Input(size=10)
		t2.td(self.name)
		
		t2.tr()
		t2.td(gui.Spacer(1,10))
		
		t2.tr()
		t2.td(gui.Label("Left: ", color = txtcolor), align=1)
		self.left = gui.Keysym()
		t2.td(self.left)
		
		t2.tr()
		t2.td(gui.Label("Right: ", color = txtcolor), align=1)
		self.right = gui.Keysym()
		t2.td(self.right)
		
		t2.tr()
		t2.td(gui.Label("Rotate CW: ", color = txtcolor), align=1)
		self.cw = gui.Keysym()
		t2.td(self.cw)
		
		t2.tr()
		t2.td(gui.Label("Rotate CCW: ", color = txtcolor), align=1)
		self.ccw = gui.Keysym()
		t2.td(self.ccw)
		
		t2.tr()
		t2.td(gui.Label("Block Down: ", color = txtcolor), align=1)
		self.down = gui.Keysym()
		t2.td(self.down)
		
		t2.tr()
		t2.td(gui.Label("Block Drop: ", color = txtcolor), align=1)
		self.drop = gui.Keysym()
		t2.td(self.drop)
		
		t2.tr()
		t2.td(gui.Label("Use Antidote: ", color = txtcolor), align=1)
		self.use_anti = gui.Keysym()
		t2.td(self.use_anti)
		
		t2.tr()
		t2.td(gui.Label("Change Target: ", color = txtcolor), align=1)
		self.change_target = gui.Keysym()
		t2.td(self.change_target)
		
		t2.tr()
		t2.td(gui.Spacer(1,10))
		
		t2.tr()
		b = gui.Button("Update", width = 50)
		b.connect(gui.CLICK,self.update_profile,None)
		t2.td(gui.Spacer(1,10))
		t2.td(b)
		
		doc.add(t2)
		t.td(doc)
		
		### Available Profiles
		doc = gui.Document(width = 200, background = (0,0,0))
		doc.add( gui.Label("Available Profiles", color = txtcolor) )
		
		
		self.profile_list = gui.List(width=145, height=150)
		names = profiles.keys()
		names.sort()
		for name in names:
			self.profile_list.add(name, value= name)
			self.profile_list.resize()
			self.profile_list.repaint()
		#self.profile_list.connect(gui.CLICK, self.select_profile, None)
		doc.add(self.profile_list)
		
		doc.space(space)
		doc.br(space[1])
		doc.br(space[1])
		
		b = gui.Button("New Profile", width = 50)
		b.connect(gui.CLICK,self.new_profile,None)
		doc.add(b)
		b = gui.Button("Edit Selected", width = 50)
		b.connect(gui.CLICK,self.select_profile,None)
		doc.add(b)
		b = gui.Button("Delete Profile", width = 50)
		b.connect(gui.CLICK,self.delete_profile,None)
		doc.add(b)
		
		doc.br(space[1])
		doc.br(space[1])
		ok_button = gui.Button("Close", width=50)
		ok_button.connect(gui.CLICK,self.to_main,None)
		doc.add(ok_button)
		
		t.td(doc)
		
		gui.Dialog.__init__(self, title, gui.ScrollArea(t,width,height))
	
	def update_profile(self, e):
		profiles = ConfigObj("profiles.cfg")
		try:
			del profiles[self.profile_list.value]
		except:
			pass
		name = self.name.value[0:8]
		if name is not None:
			profiles[name] = {}
			profiles[name]["Left"] = self.left.value
			profiles[name]["Right"] = self.right.value
			profiles[name]["CW"] = self.cw.value
			profiles[name]["CCW"] = self.ccw.value
			profiles[name]["Down"] = self.down.value
			profiles[name]["Drop"] = self.drop.value
			profiles[name]["Anti"] = self.use_anti.value
			profiles[name]["Change"] = self.change_target.value
		
		profiles.write()
		self.profile_list.clear()
		names = profiles.keys()
		names.sort()
		for name in names:
			self.profile_list.add(name, value= name)
		self.profile_list.resize()
		self.profile_list.repaint()
		
	def select_profile(self, e):
		profiles = ConfigObj("profiles.cfg")
		name = self.profile_list.value
		if name is not None and profiles.has_key(name):
			self.name.value = name
			self.left.value = profiles[name]["Left"]
			self.right.value = profiles[name]["Right"]
			self.cw.value = profiles[name]["CW"]
			self.ccw.value = profiles[name]["CCW"]
			self.down.value = profiles[name]["Down"]
			self.drop.value = profiles[name]["Drop"]
			self.use_anti.value = profiles[name]["Anti"]
			self.change_target.value = profiles[name]["Change"]
		
	def new_profile(self, e):
		profiles = ConfigObj("profiles.cfg")
		print "."
		new_name = "Player"
		while profiles.has_key(new_name):
			new_name += "_"
		
		profiles[new_name] = {"Left":"100",
						"Right":"100",
						"CW":"100",
						"CCW":"100",
						"Down":"100",
						"Drop":"100",
						"Anti":"100",
						"Change":"100"}
		profiles.write()
		self.profile_list.clear()
		names = profiles.keys()
		names.sort()
		for name in names:
			self.profile_list.add(name, value= name)
		self.profile_list.resize()
		self.profile_list.repaint()
		
	def delete_profile(self, e):
		profiles = ConfigObj("profiles.cfg")
		try:
			del profiles[self.profile_list.value]
		except:
			pass
		profiles.write()
		self.profile_list.clear()
		names = profiles.keys()
		names.sort()
		for name in names:
			self.profile_list.add(name, value= name)
		self.profile_list.resize()
		self.profile_list.repaint()
		
	def event(self, e):
		if e.type == KEYDOWN and e.key == K_ESCAPE:
			self.to_main(e)
		else:
			gui.Dialog.event(self, e)

	def to_main(self, e):
		self.close()


class HelpDialog(gui.Dialog):
	def __init__(self):
		title = gui.Label("Help")
		
		width = 500
		height = 320
		
		txtcolor = (0,255,0)
		bgcolor = (0,0,0)
		special = pygame.image.load(os.path.join("images", "special.png"))
		blocks = []
		for b in range(22):
			block = pygame.Surface((24,24))
			block.blit(special, (0,0), pygame.Rect((b*24, 0), (b*24+24, 24)))
			blocks.append(block)
			
		space = title.style.font.size(" ")
		
		c = gui.Container(background = bgcolor)
		
		### Main text
		txt = "".join(["Eit is a tetris version based on Eittris ", 
			"featuring up to 4 player head-to-head combat. ",
			"Eit features 22 power-up blocks such as Blind and Clear, ",
			"making the gameplay extra interesting!"])
		doc = gui.Document(width = 200, background=bgcolor)
		for word in txt.split(" "): 
			doc.add(gui.Label(word, color = txtcolor))
			doc.space(space)
		c.add(doc, 20,50)
		
		### Special Blocks
		t = gui.Table(width = 250, height = 320, background = bgcolor)
		t.tr()
		t.td( gui.Image(blocks[0]), align = -1 )
		t.td(gui.Label( "Rabbit", color= txtcolor ), align = -1)		
		t.td( gui.Image(blocks[1]), align = -1 )
		t.td(gui.Label( "Turtle", color = txtcolor), align = -1)
		
		t.tr()
		t.td( gui.Image(blocks[2]), align = -1 )
		t.td(gui.Label( "Stair", color = txtcolor), align = -1)		
		t.td( gui.Image(blocks[3]), align = -1 )
		t.td(gui.Label( "Fill", color = txtcolor), align = -1)
		
		t.tr()
		t.td( gui.Image(blocks[4]), align = -1 )
		t.td(gui.Label( "Rumble", color = txtcolor), align = -1)		
		t.td( gui.Image(blocks[5]), align = -1 )
		t.td(gui.Label( "Inverse", color = txtcolor), align = -1)
		
		t.tr()
		t.td( gui.Image(blocks[6]), align = -1 )
		t.td(gui.Label( "Switch", color = txtcolor), align = -1)		
		t.td( gui.Image(blocks[7]), align = -1 )
		t.td(gui.Label( "Packet", color = txtcolor), align = -1)
		
		t.tr()
		t.td( gui.Image(blocks[8]), align = -1 )
		t.td(gui.Label( "Yin & Yang", color = txtcolor), align = -1)		
		t.td( gui.Image(blocks[9]), align = -1 )
		t.td(gui.Label( "Mini", color = txtcolor), align = -1)
		
		t.tr()
		t.td( gui.Image(blocks[10]), align = -1 )
		t.td(gui.Label( "Blink", color = txtcolor), align = -1)		
		t.td( gui.Image(blocks[11]), align = -1 )
		t.td(gui.Label( "Blind", color = txtcolor), align = -1)
		
		t.tr()
		t.td( gui.Image(blocks[12]), align = -1 )
		t.td(gui.Label( "Background", color = txtcolor), align = -1)		
		t.td( gui.Image(blocks[13]), align = -1 )
		t.td(gui.Label( "Antidote", color = txtcolor), align = -1)
		
		t.tr()
		t.td( gui.Image(blocks[14]), align = -1 )
		t.td(gui.Label( "Bridge", color = txtcolor), align = -1)		
		t.td( gui.Image(blocks[15]), align = -1 )
		t.td(gui.Label( "Ice", color = txtcolor), align = -1)
		
		t.tr()
		t.td( gui.Image(blocks[16]), align = -1 )
		t.td(gui.Label( "Clear", color = txtcolor), align = -1)		
		t.td( gui.Image(blocks[17]), align = -1 )
		t.td(gui.Label( "Question", color = txtcolor), align = -1)
		
		t.tr()
		t.td( gui.Image(blocks[18]), align = -1 )
		t.td(gui.Label( "SZ", color = txtcolor), align = -1)		
		t.td( gui.Image(blocks[19]), align = -1 )
		t.td(gui.Label( "Blackout", color = txtcolor), align = -1)
		
		t.tr()
		t.td( gui.Image(blocks[20]), align = -1 )
		t.td(gui.Label( "Ring", color = txtcolor), align = -1)
		
		t.tr()
		t.td( gui.Image(blocks[21]), align = -1 )
		t.td(gui.Label( "Castle", color = txtcolor), align = -1)
		
		c.add(t, 250, 0)
		
		### OK
		b = gui.Button("Close", width = 50)
		b.connect(gui.CLICK,self.close,None)
		c.add(b, 395, 270)
		
		gui.Dialog.__init__(self, title, gui.ScrollArea(c,width,height))

class SelectProfileDialog(gui.Dialog):
	def __init__(self):
		title = gui.Label("Select a Profile")
		
		width = 160
		height = 160
		bgcolor = (0,0,0)
		c = gui.Container(background = bgcolor)
		
		doc = gui.Document(width=width, background = bgcolor)
		
		space = (5,5) #title.style.font.size(" ")
		
		
		doc.block(align=1)
		
		profiles = ConfigObj("profiles.cfg")
		self.profile_list = gui.List(width=155, height=120)
		names = profiles.keys()
		names.sort()
		for name in names:
			self.profile_list.add(name, value = name)
		self.profile_list.resize()
		self.profile_list.repaint()
		
		doc.add(self.profile_list)
		doc.space(space)
		doc.br(space[1])
		doc.br(space[1])
		
		t = gui.Table(width = 155, height = 30, background = bgcolor)
		
		ok_button = gui.Button("Ok", width=55)
		ok_button.connect(gui.CLICK,self.send,gui.CHANGE)
		#ok_button.connect(gui.CLICK,self.to_main,None)
		t.tr()
		t.td(ok_button)
		
		b = gui.Button("Cancel", width=55)
		b.connect(gui.CLICK,self.close,None)
		t.td(b)
		
		doc.add(t)
		c.add(doc, 0,0)
		gui.Dialog.__init__(self, title, gui.ScrollArea(c,width,height))
	
	def open(self, *params):
		profiles = ConfigObj("profiles.cfg")
		self.profile_list.clear()
		names = profiles.keys()
		names.sort()
		for name in names:
			self.profile_list.add(name, value = name)
		gui.Dialog.open(self, *params)
		
	def cancel(self, e):
		self.send(gui.CHANGE)
		self.profile_list.value = "None"
		
	
	def event(self, e):
		if e.type == KEYDOWN and e.key == K_ESCAPE:
			self.to_main(e)
		else:
			gui.Dialog.event(self, e)
	"""
	def close(self,e=None):
		name = self.profile_list.value
		gui.Dialog.close(self,e)
		if name is not None:
			return name
		else:
			return None
	"""	
	def to_main(self, e):
		#self.profile_list.value = None
		self.close()

class ViewScoreDialog(gui.Dialog):
	def __init__(self, scoretable):
		title = gui.Label("Highscores")
		
		width = 450
		height = 250
		bgcolor = (0,0,0)
		txtcolor = (0,255,0)
		c = gui.Container(background = bgcolor)
		
		doc = gui.Document(width=width, background = bgcolor)
		
		space = (5,5) #title.style.font.size(" ")
		
		doc.block(align=0)
		"""
		for word in "Highscores!".split(" "): 
			doc.add(gui.Label(word, color = txtcolor))
			doc.space(space)
		"""
		doc.br(space[1])
		"""
		self.stats = {"Test":{"Matches":0, "Score":0, "Lines":0, "Max Level":0, 
							  "Rank Points":0, "Winns":0}}
		"""
		t = gui.Table(width=445, height=200)
		t.tr()
		t.td( gui.Label("Rank Pts", color = txtcolor) )
		t.td( gui.Label("Name", color = txtcolor) )
		t.td( gui.Label("Tot Score", color = txtcolor) )
		t.td( gui.Label("Tot Lines", color = txtcolor) )
		t.td( gui.Label("Max Lvl", color = txtcolor) )
		t.td( gui.Label("W/L", color = txtcolor) )
		t.tr()
		t.td(gui.Spacer(1,10))
		place = 1
				
		l = scoretable.get_list()
		for name, stat in l:
			t.tr()
			t.td(gui.Label( str(stat["Rank Points"]), color = txtcolor ))
			t.td(gui.Label( name, color = txtcolor ))
			t.td(gui.Label( str(stat["Score"]), color = txtcolor ))
			t.td(gui.Label( str(stat["Lines"]), color = txtcolor ))
			t.td(gui.Label( str(stat["Max Level"]), color = txtcolor ))
			t.td(gui.Label( str(stat["Winns"]) + "/" + str(stat["Matches"] - stat["Winns"]), 
						    color = txtcolor ))
			
		doc.add(t)
		
		
		t = gui.Table(width = 155, height = 30, background = bgcolor)
		
		#ok_button = gui.Button("Ok", width=55)
		#ok_button.connect(gui.CLICK,self.send,gui.CHANGE)
		t.tr()
		#t.td(ok_button)
		
		b = gui.Button("Ok", width=55)
		b.connect(gui.CLICK,self.close,None)
		t.td(b)
		
		doc.add(t)
		c.add(doc, 0,0)
		gui.Dialog.__init__(self, title, gui.ScrollArea(c,width,height))

class EnterScoreDialog(gui.Dialog):
	def __init__(self,score):
		self.score = score
				
		hs = high.High("highscore.dat")
		if hs.check(self.score) is None:
			self.gotscore = False
			self.close()
			return
		self.gotscore = True
		#self.app = gui.Desktop(width=400,height=200)
		#self.app.connect(gui.KEYDOWN, self.handle_key_press)
		
		title = gui.Label("Enter Highscore")
		c = gui.Table()	
		
		self.i = gui.Input(value='Bzzzz', size=15)
		self.i.connect(gui.CLICK, self.clear_name)
		self.i.connect(gui.KEYDOWN, self.handle_key_press)
		
		self.ok_button = gui.Button("ok", width=150)
		self.ok_button.connect(gui.CLICK,self.to_main,None)
		
		txt = "You got " + str(int(score/64)) + "honey jars"+ "!"
		c.tr()
		c.td(gui.Label(txt))
		c.tr()
		c.td(gui.Spacer(1,10))
		c.tr()
		c.td(gui.Label("Enter Name:"))
		c.tr()
		c.td(self.i)
		c.tr()
		c.td(self.ok_button)
		
		gui.Dialog.__init__(self,title,c)
		
	def to_main(self,e):
		hs = high.High("highscore.dat")
		hs.submit(self.score, self.i.value)
		hs.save()
		self.close()
		print self.i.value
		
		
	def handle_key_press(self, _event):
		if self.i.value == "":
			self.ok_button.disabled = True
		else:
			self.ok_button.disabled = False
		
	def clear_name(self):
		self.i.value = ""
		self.ok_button.disabled = True
		