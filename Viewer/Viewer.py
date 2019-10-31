'''
File: Viewer.py
Author: Morgan R. & Seth S.
Date: 06/04/19
Description: This viewer can be run on a RaspberryPI, and pulls timelapse photos from a webserver hosted by Server.py
'''

from kivy.config import Config
import timelapseshare as tls
import PIL
import _thread
import time
import os
os.environ['KIVY_GL_BACKEND'] = 'gl' # FIXES A SEGFAULT ????
import urllib.request as urllib
#Config.set('graphics', 'fullscreen','auto')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
#Config.set('kivy', 'exit_on_escape', '1')

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.graphics import Rectangle, Color
from kivy.clock import Clock

# ==========================
#	Defaults
# ==========================

_SPEED = 1
_UPDATE_INTERVAL = 10 # every 10 seconds
_CLEAR_CACHE = False
_FILESERVER = "http://localhost:8000"

# ==========================
#	Command-Line Arguments
# ==========================

import argparse
import platform

def dir_path(string):
	if os.path.isdir(string):
		return string
	else:
		raise

parser = argparse.ArgumentParser(description="Interactive Timelapse scroller")
parser.add_argument("-i", "--image_directory", type=dir_path, help="Sets the directory where the images are stored")
parser.add_argument("-pre", "--image_prefix", type=str, help="Sets the prefix of the image Eg. 'IMG'")
parser.add_argument("-post", "--image_postfix", type=str, help="Sets the postfix of the image Eg. '.jpg'")
parser.add_argument("-url", "--server_url", type=str, help="Sets the link to the server hosted by the webcam")

args = parser.parse_args()

if args.image_directory:
	print("[*] SETTING IMAGE DIRECTORY : " + args.image_directory)
	tls.setImageDirectory(args.image_directory)

if args.server_url:
	print("[*] SETTING URL TO SERVER : " + args.server_url)
	_FILESERVER = args.server_url

# ==========================
#	Runtime Calculations
# ==========================

tls.updateStats()

def getImageDateTime(ID):
	datafile = open(tls.getDataByID(ID))
	teasis = datafile.read()
	datafile.close()
	return teasis

print("Highest: %d\nLowest: %d" % (tls.getMax(), tls.getMin()))

# ==========================
#	WebServer stuff
# ==========================

def update_imgs(min_i, max_i):
	global _CLEAR_CACHE
	if tls._MIN > min_i and _CLEAR_CACHE:
		for i in range(tls._MIN, min_i): # delete files in that range
			try:
				print("removing " + str(i))
				os.remove(tls.getImageByID(i))
			except:
				print(str(i) + " doesn't exist!")

	if tls._MAX < max_i:
		for i in range(tls._MAX, max_i): # gets files in that range
			try:
				print("retrieving " + str(i))
				urllib.urlretrieve(_FILESERVER + "/frame" + str(i) + ".jpg", tls.getImageByID(i))
			except:
				print(str(i) + " doesn't exist!")
	tls.updateStatsManually(min_i, max_i)

def get_update():
	try:
		urllib.urlretrieve(_FILESERVER + "/index.txt", "index.txt")
		indx = open("index.txt")
		lines = indx.readlines()
		mi = int(lines[0])
		ma = int(lines[1])
		update_imgs(mi, ma)
		return True
	except:
		print("server down!")
		return False

# ==========================
#	Update thread
# ==========================

get_update()

def update_loop():
	global _UPDATE_INTERVAL
	while True:
		time.sleep(_UPDATE_INTERVAL)
		get_update()

_thread.start_new_thread(update_loop, ())

# ==========================
#	User-Interface
# ==========================

class DebugScreen(Screen):
	def __init__(self, *args, **kwargs):
		super(DebugScreen, self).__init__(*args, **kwargs)
		self.index = tls._MIN

		master_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.1))
		self.title = Label(text='', font_size=80, size_hint=(1, 1))

		master_layout.add_widget(self.title)

		background_container = FloatLayout()
		self.image = Image(source=tls.getImageByID(self.index), size_hint=(1, 0.9), nocache=True, allow_stretch=True)

		background_container.add_widget(self.image)
		background_container.add_widget(master_layout)

		self.add_widget(background_container)

		Clock.schedule_interval(self.updateScroll, 0.10)
		Clock.schedule_interval(self.TLS_update, 1)

		# Keyboard Input
		self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
		self._keyboard.bind(on_key_down=self._on_keyboard_down, on_key_up=self._on_keyboard_up)

		self.leftKey = False
		self.rightKey = False

		self.leftCount = 0
		self.rightCount = 0

		self.velo = 0

	# Keyboard callbacks

	def _keyboard_closed(self):
		self._keyboard.unbind(on_key_down=self._on_keyboard_down)
		self._keyboard = None

	def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
		if keycode[1] == 'left':
			self.leftKey = True
		elif keycode[1] == 'right':
			self.rightKey = True
		return True

	def _on_keyboard_up(self, keyboard, keycode):
		if keycode[1] == 'left':
			self.leftKey = False
		elif keycode[1] == 'right':
			self.rightKey = False
		return True

	# Mouse callbacks

	def on_touch_down(self, touch):
		if touch.is_mouse_scrolling:
			if touch.button == 'scrolldown':
				if self.index > tls._MIN:
					self.index = self.index - _SPEED
			elif touch.button == 'scrollup':
				if self.index < tls._MAX:
					self.index = self.index + _SPEED
		GridLayout.on_touch_down(self, touch)

	def updateScroll(self, *args):
		app = App.get_running_app()

		if self.leftKey:
			if self.leftCount >= 4:
				self.velo = -4
			else:
				self.velo = self.velo - 1
		elif self.rightKey:
			if self.rightCount >= 4:
				self.velo = 4
			else:
				self.velo = self.velo + 1
		else:
			self.velo = 0
			self.leftCount = 0
			self.rightCount = 0

		if (self.index+self.velo) > tls._MAX or (self.index+self.velo) < tls._MIN:
			if (self.index+self.velo) > tls._MAX:
				self.index = tls._MAX
			elif (self.index+self.velo) < tls._MIN:
				self.index = tls._MIN
		else:
			self.index = self.index+self.velo
			#print("moving : " + str(self.index))

		try:
			self.title.text = tls.getTimeByID(self.index)
			self.image.source = tls.getImageByID(self.index)
		except:
			pass

	# Timelapse Share auto-updating stuff

	def TLS_update(self, *args):
		#tls.updateStats();

		if self.index > tls._MAX:
			self.index = tls._MAX
		if self.index < tls._MIN:
			self.index = tls._MIN

		try:
			self.title.text = tls.getTimeByID(self.index)
			self.image.source = tls.getImageByID(self.index)
		except:
			pass

class ScreenManagement(ScreenManager):
	def __init__(self, *args, **kwargs):
		super(ScreenManagement, self).__init__(*args, **kwargs)

		self.DBscreen = DebugScreen(name='scrollDebug')

		self.add_widget(self.DBscreen)

		self.current = 'scrollDebug'

class MainApp(App):
	def build(self):
		self.manager = ScreenManagement(transition=NoTransition())
		return(self.manager)

# Start the app
MainApp().run()
