'''
File: Server.py
Author: Morgan R. & Seth S.
Date: 06/04/19
Description: This creates a Timelapse from a camera, and hosts the files on a webserver. The Min and Max frames are located at /index.txt.
	Any client can pull the index.txt info and pull their missing frames.
'''

import cv2
import time
try: # Python 2
	import thread
	from SimpleHTTPServer import SimpleHTTPRequestHandler
	from BaseHTTPServer import HTTPServer as BaseHTTPServer
except: # Python 3
	import _thread
	from http.server import SimpleHTTPRequestHandler
	from http.server import HTTPServer as BaseHTTPServer

from PIL import Image
from PIL.ExifTags import TAGS
import piexif
from time import gmtime, strftime
import os
import argparse
import timelapseshare as tls

# ==========================
#	Defaults
# ==========================

_ITERATION = 1 # minuets
_MAXPHOTOS = 45000
_DEBUG = True # shows frame window
_PORT = 8000 # port the fileserver is hosted on

_LAST_TIME = time.time()

# ==========================
#	Command-line Arguments
# ==========================

def dir_path(string):
	if os.path.isdir(string):
		return string
	else:
		raise

parser = argparse.ArgumentParser(description="Timelapse Taker for a Raspberry Pi")
parser.add_argument("-idir", "--image_directory", type=dir_path, help="Sets the directory where the images are stored")
parser.add_argument("-t", "--time", type=float, help="Sets the minuets between shots, Eg, 1")
parser.add_argument("-m", "--max", type=int, help="Sets the max amount of shots before deleting old ones, Eg. 45000")
parser.add_argument("-p", "--port", type=int, help="Sets the port the server is hosted on, Eg. 8000")
args = parser.parse_args()

if args.image_directory:
	print("[*] SETTING IMAGE DIRECTORY : " + args.image_directory)
	tls.setImageDirectory(args.image_directory)

if args.time:
	print("[*] SETTING TIME BETWEEN SHOTS : " + str(args.time))
	_ITERATION = args.time

if args.max:
	print("[*] SETTING MAX AMMOUNT OF SHOTS : " + str(args.max))
	_MAXPHOTOS = args.max

if args.port:
	print("[*] SETTING PORT TO HOST SERVER ON")
	_PORT = args.port

# ==========================
#	Runtime Calculations
# ==========================

tls.updateStats()

print("Highest: %d\nLowest: %d" % (tls.getMax(), tls.getMin()))

# ==========================
#	FileServer from any directory
# ==========================

class HTTPHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(self.server.base_path, relpath)
        return fullpath

class HTTPServer(BaseHTTPServer):
    def __init__(self, base_path, server_address, RequestHandlerClass=HTTPHandler):
        self.base_path = base_path
        BaseHTTPServer.__init__(self, server_address, RequestHandlerClass)

def serveImages(direct, port):
	web_dir = os.path.join(os.path.dirname(__file__), direct)
	httpd = HTTPServer(web_dir, ("", port))
	httpd.serve_forever()

# updates a file that the client pulls and checks against
def updateDataFile(mi, ma):
	f = open("images/index.txt", "w")
	f.write(str(mi))
	f.write("\n")
	f.write(str(ma))
	f.close()

try:
	_thread.start_new_thread(serveImages, ('images', _PORT))
except:
	print("thread failed!")
	exit(0)

# ==========================
#	OpenCV2 & Main loop
# ==========================

cam = cv2.VideoCapture(0)
cv2.namedWindow('TimelapseCam', cv2.WINDOW_NORMAL)
ID = tls.getMax()
checkpoint = tls.getMin()

# update the file first
updateDataFile(checkpoint, ID)

while True:
	success, image = cam.read()
	if success:
		cv2.imshow('TimelapseCam', image)
		if time.time() - _LAST_TIME > (_ITERATION*60):
			dumppath = tls.getImageByID(ID)
			print("dumping frame %d to %s" % (ID, dumppath))
			cv2.imwrite('temp.jpeg', image) # writes a temp file

			# WRITE THE TIMESTAMP TO EXIF, OPENCV2 DOESN'T WRITE EXIF :(
			im = Image.open('temp.jpeg')
			exif_dict = piexif.load('temp.jpeg')
			exif_dict["0th"][piexif.ImageIFD.DateTime]=strftime("%Y-%m-%d %H:%M:%S", gmtime())
			exif_bytes = piexif.dump(exif_dict)

			# save :)
			im.save(dumppath, "jpeg", exif=exif_bytes, quality="keep", optimize=True)

			updateDataFile(checkpoint, ID)

			ID = ID +1
			_LAST_TIME = time.time()

			if (ID - checkpoint) > _MAXPHOTOS:
				print("removing frame %d" % checkpoint)
				os.remove(tls.getImageByID(checkpoint))
				checkpoint = checkpoint + 1
	key = cv2.waitKey(1)
	if key == 27:
		break;
