import sys
import os
import uuid
import cv2
import shutil
import subprocess
import datetime
import json
import traceback
#import tensorflow as tf
from PIL import Image
import io
import glob


TENSORFLOW_DIR = "/home/playground/tensorflow/"
VIDEO_DIR_NSFW = "/home/playground/training/nsfw-detection/videos/nsfw/" #"C:\\imagemonkey-nsfw\\training\\nsfw-model\\videos\\nsfw\\"
VIDEO_DIR_SFW = "/home/playground/training/nsfw-detection/videos/sfw/" #"C:\\imagemonkey-nsfw\\training\\nsfw-model\\videos\\sfw\\"
FRAMES_DIR = "/home/playground/training/nsfw-detection/frames/" #"C:\\imagemonkey-nsfw\\training\\nsfw-model\\frames\\"
FRAMES_DIR_NSFW = FRAMES_DIR + "nsfw" + os.path.sep
FRAMES_DIR_SFW = FRAMES_DIR + "sfw" + os.path.sep

TMP_GRAPH_OUTPUT_PATH = "/tmp/output_graph_nsfw.pb"
TMP_LABELS_OUTPUT_PATH = "/tmp/output_labels_nsfw.txt"

GRAPH_OUTPUT_PATH= "/home/playground/training/models/nsfw/graph.pb"
LABELS_OUTPUT_PATH = "/home/playground/training/models/nsfw/labels.txt"

CONFIG_FILE_PATH = "/home/playground/training/conf/nsfw.json" #"C:\\imagemonkey-nsfw\\conf\\input.json"
YOUTUBE_DL_PATH = "/home/playground/bin/youtube-dl" #"C:\\imagemonkey-nsfw\\youtube-dl.exe"
VIDEO_CACHE_PATH = "/home/playground/training/nsfw-detection/videos/cache.tmp"

MODEL_INFO_PATH  = "/home/playground/training/models/nsfw/model_info.json"

class VideoCacheEntry(object):
	def __init__(self):
		self._url = None
		self._filePath = None
		self._filename = None
		self._isNSFW = None

	@property
	def url(self):
		return self._url

	@url.setter
	def url(self, u):
		self._url = u

	@property
	def filepath(self):
		return self._filePath

	@filepath.setter
	def filepath(self, f):
		self._filePath = f

	@property
	def filename(self):
		return self._filename

	@filename.setter
	def filename(self, f):
		self._filename = f

	@property
	def isNSFW(self):
		return self._isNSFW

	@isNSFW.setter
	def isNSFW(self, isNSFW):
		self._isNSFW = isNSFW

	def toDict(self):
		d = {}
		d["is_nsfw"] = self._isNSFW
		d["filepath"] = self._filePath
		d["filename"] =self._filename
		d["url"] = self._url

		return d





class VideoCache(object):
	def __init__(self):
		self._path = VIDEO_CACHE_PATH
		self._cache = {}

		if os.path.isfile(self._path):
			with open(self._path) as f:    
				data = json.load(f)
				for key in data:
					v = VideoCacheEntry()
					v.isNSFW = data[key]["is_nsfw"]
					v.filepath = data[key]["filepath"]
					v.filename = data[key]["filename"]
					v.url = data[key]["url"]
					self._cache[v.url] = v

	def contains(self, key):
		if key in self._cache:
			return True
		return False

	def value(self, key):
		if key in self._cache:
			return self._cache[key]
		return None

	def insert(self, e):
		data = {}
		if os.path.isfile(self._path):
			with open(self._path) as f:    
				data = json.load(f)

		data[e.url] = e.toDict()
		self._cache[e.url] = e

		with open(self._path, 'w') as outfile:
			json.dump(data, outfile)



class Video(object):
	def __init__(self, url, isNSFW,videoCache):
		self._url = url
		self._isNSFW = isNSFW
		self._filename = None
		self._filePath = None
		self._videoCache = videoCache

	def download(self):
		filePath = None

		if self._videoCache.contains(self._url):
			videoCacheEntry = self._videoCache.value(self._url)
			self._filename = videoCacheEntry.filename
			self._filePath= videoCacheEntry.filepath
			print "Cache already contains entry for url %s" %(self._url,)

		else:
			u = str(uuid.uuid4())
			if self._isNSFW:
				filePath = VIDEO_DIR_NSFW + u
				cmd = YOUTUBE_DL_PATH + " -o " + VIDEO_DIR_NSFW + u + " " + self._url
			else:
				filePath = VIDEO_DIR_SFW + u
				cmd = YOUTUBE_DL_PATH + " -o " + VIDEO_DIR_SFW + u +  " " + self._url
			print "Downloading %s" %(self._url,)
			p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
			out, err = p.communicate()
			if p.returncode != 0:
				print "Couldn't download %s " %(self._url,)
				return False
			else: #download successful
				self._filename = u
				self._filePath = filePath
				print "Download %s successful" %(self._url,)
				self._filePath = self._getActualFilePath()

				videoCacheEntry = VideoCacheEntry()
				videoCacheEntry.url = self._url
				videoCacheEntry.filename = self._filename
				videoCacheEntry.filepath = self._filePath
				videoCacheEntry.isNSFW = self._isNSFW

				self._videoCache.insert(videoCacheEntry)



		return True

	def _getActualFilePath(self):
		files = glob.glob((self._filePath+"*"))
		if(len(files) == 0):
			return self._filePath
		elif(len(files) == 1):
			return files[0]
		else:
			print "Found more than one file...picking first one"
			return files[0]
		

	"""def toFrames(self):
		if self._isNSFW:
			outputDir = FRAMES_DIR_NSFW
		else:
			outputDir = FRAMES_DIR_SFW

		print self._filePath
		vidcap = cv2.VideoCapture(self._filePath)
		success, image = vidcap.read()
		count = 0
		success = True
		while success:
			success,image = vidcap.read()
			print 'Read a new frame: %d' %(count,)
			cv2.imwrite((outputDir + str(uuid.uuid4()) + ".jpg"), image) # save frame as JPEG file
			count += 1"""

	def toFrames(self):
		fps = 1 #frames per second
		if self._isNSFW:
			outputDir = FRAMES_DIR_NSFW
		else:
			outputDir = FRAMES_DIR_SFW

		cmd = "ffmpeg -i " + self._filePath + " -vf fps=" + str(fps) + " " + outputDir + self._filename + "%08d.jpg"
		print cmd
		p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
		out, err = p.communicate()
		if p.returncode != 0:
			print "Couldn't create frames for video %s" %(self._filePath,)
			return False
		print "Created frames for video %s" %(self._filePath,)
		return True

	

def trainModel():
	cmd = ("python " + TENSORFLOW_DIR + "tensorflow" + os.path.sep + "examples" + os.path.sep + 
			"image_retraining" + os.path.sep + "retrain.py" + " --image_dir " + FRAMES_DIR + os.path.sep
			+ " --output_graph " + TMP_GRAPH_OUTPUT_PATH + " --output_labels " + TMP_LABELS_OUTPUT_PATH)
	 
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
	out, err = p.communicate()
	if p.returncode != 0:
		print "Couldn't retrain model!"
		return False
	else: #model creation successful
		shutil.copyfile(TMP_GRAPH_OUTPUT_PATH, GRAPH_OUTPUT_PATH) 
		shutil.copyfile(TMP_LABELS_OUTPUT_PATH, LABELS_OUTPUT_PATH)
	return True


def cleanupTrainingDir():
	#cleanup sfw directory
	for f in os.listdir(FRAMES_DIR_SFW):
	    filePath = os.path.join(FRAMES_DIR_SFW, f)
	    try:
	        if os.path.isfile(filePath):
	            os.unlink(filePath)
	        elif os.path.isdir(filePath): shutil.rmtree(filePath)
	    except Exception as e:
	        print(e)
	        return False

	#cleanup nsfw directory
	for f in os.listdir(FRAMES_DIR_NSFW):
	    filePath = os.path.join(FRAMES_DIR_NSFW, f)
	    try:
	        if os.path.isfile(filePath):
	            os.unlink(filePath)
	        elif os.path.isdir(filePath): shutil.rmtree(filePath)
	    except Exception as e:
	        print(e)
	        return False

	return True


def parseConfigFile():
	videoCache = VideoCache()

	with open(CONFIG_FILE_PATH) as f:    
		data = json.load(f)

	nsfwVideos = data["videos"]["nsfw"]
	sfwVideos = data["videos"]["sfw"]

	videos = []
	for nsfwVideo in nsfwVideos:
		v = Video(nsfwVideo["url"], True, videoCache)
		videos.append(v) 

	for sfwVideo in sfwVideos:
		v = Video(sfwVideo["url"], False, videoCache)
		videos.append(v)

	return videos

def writeModelInfo(categories):
	data = {}
	now = datetime.datetime.now()

	try:
		if os.path.isfile(MODEL_INFO_PATH):
			with open(MODEL_INFO_PATH) as f:   
				data = json.load(f)
				data["build"] = data["build"] + 1
				data["created"] = now.strftime("%Y-%m-%d %H:%M")
				data["based_on"] = "inception-v3"
				data["trained_on"] = categories
		else:
			data["build"] = 1
			data["created"] = now.strftime("%Y-%m-%d %H:%M")
			data["based_on"] = "inception-v3"
			data["trained_on"] = categories
		with open(MODEL_INFO_PATH, 'w') as outfile:
			json.dump(data, outfile)
	except:
		print traceback.print_exc()
		return False
	return True


if __name__ == "__main__":
	cleanupTrainingDir()

	videos = parseConfigFile()
	for video in videos:
		video.download()
		video.toFrames()

	trainModel()

	writeModelInfo(["sfw", "nsfw"])

	#download("https://www.youtube.com/watch?v=lzWLsyTqnhk", False)
	#video2frames("C:\\imagemonkey-nsfw\\training\\sfw\\videos\\e7b428d5-00ea-444e-8bf0-a08a241b7779", False)