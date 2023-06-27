from distutils.core import setup
import glob
import os
from py2exe.build_exe import py2exe

class Py2exe(py2exe): 
	"""From py2exe wiki, adds the upx option to compress files"""
	def initialize_options(self): 
		# Add a new "upx" option for compression with upx 
		py2exe.initialize_options(self) 
		self.upx = 0 
	def copy_file(self, *args, **kwargs): 
		# Override to UPX copied binaries. 
		(fname, copied) = result = py2exe.copy_file(self, *args, **kwargs) 

		basename = os.path.basename(fname) 
		if (copied and self.upx and 
			(basename[:6]+basename[-4:]).lower() != 'python.dll' and 
			fname[-4:].lower() in ('.pyd', '.dll')): 
			os.system('upx --best "%s"' % os.path.normpath(fname)) 
		return result 

	def patch_python_dll_winver(self, dll_name, new_winver=None): 
		# Override this to first check if the file is upx'd and skip if so 
		if not self.dry_run: 
			if not os.system('upx -qt "%s" >nul' % dll_name): 
				if self.verbose: 
					print "Skipping setting sys.winver for '%s' (UPX'd)" % dll_name 
			else: 
				py2exe.patch_python_dll_winver(self, dll_name, new_winver) 
				# We UPX this one file here rather than in copy_file so 
				# the version adjustment can be successful 
				if self.upx: 
					os.system('upx --best "%s"' % os.path.normpath(dll_name)) 

setup(windows=["eit.py"],
	options = {'py2exe': {'upx' : 0}},
	cmdclass = {'py2exe': Py2exe},
	data_files=[(os.path.join("data", "themes", "eit"),
				glob.glob(os.path.join("data", "themes", "eit") + """\*""")),
			("default",
				glob.glob(os.path.join("data", "themes", "default") + """\*""")),
			("fonts", 
				glob.glob("""fonts\*.ttf""")),
			("images",
				glob.glob("""images\*.png""")),
			(os.path.join("images","backgrounds"),
				glob.glob(os.path.join("images","backgrounds") + """\*.png""")),
			("music",
				glob.glob("""music\*.*""")),
			("sounds",
				glob.glob("""sounds\*.WAV""")),
			("source",
				glob.glob("*.py") + ["makeExe.bat"]),
			(os.path.join("source", "pgu"),
				glob.glob("pgu\*.py")),
			(os.path.join("source", "pgu", "gui"),
				glob.glob(os.path.join("pgu", "gui") + """\*.py""")),
			("",
				["gpl.txt", "license.txt", "licenses.txt", "profiles.cfg", "settings.cfg"])],
	)
