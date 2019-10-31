import glob
import piexif

_IMAGE_DIRECTORY = './images/'
_IMAGE_PRE = 'frame'
_IMAGE_POST = '.jpg'
_DATA_POST = '.txt'
_MIN = 1
_MAX = 1

def getFrames():
	return glob.glob(_IMAGE_DIRECTORY + '*' + _IMAGE_POST)
	
def getID(path):
	return path.replace(_IMAGE_DIRECTORY, '').replace(_IMAGE_PRE, '').replace(_IMAGE_POST, '')

def getMin():
	frames = getFrames()
	lowest = 50000
	for f in frames:
		ID = getID(f)
		if int(ID) < int(lowest):
			lowest = int(ID)
	return lowest

def getMax():
	frames = getFrames()
	highest = 0
	for f in frames:
		ID = getID(f)
		if int(ID) > highest:
			highest = int(ID)
	return highest
	
def getImageByID(index):
	return (_IMAGE_DIRECTORY + _IMAGE_PRE + str(index) + _IMAGE_POST)
	
def getTimeByID(index):
	exif_dict = piexif.load(getImageByID(index))
	t = str(exif_dict["0th"][piexif.ImageIFD.DateTime]).replace('b\'', '') # gets timestamp from exif
	return t[:len(t)-1] # removes trailing "'"

def setImageDirectory(dire):
	_IMAGE_DIRECTORY = dire
	
def updateStatsManually(mi, ma):
	global _MIN
	global _MAX
	_MIN = mi
	_MAX = ma

def updateStats():
	global _MIN
	global _MAX
	_MIN = getMin();
	_MAX = getMax();
