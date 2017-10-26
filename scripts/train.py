#!/usr/bin python

import sys
import os
import requests
import shutil
import subprocess
import datetime
import json
import traceback
import tensorflow as tf
from PIL import Image
import io

TENSORFLOW_MODELS_DIR = "/home/playground/tensorflow_models"

sys.path.append(TENSORFLOW_MODELS_DIR + os.path.sep + "research" + os.path.sep)

from object_detection.utils import dataset_util

TENSORFLOW_DIR = "/home/playground/tensorflow/"
BASEURL = "https://api.imagemonkey.io/v1/"
DONATIONS_DIR = "/home/playground/donations/"
CATEGORIES_DIR = "/home/playground/training/categories/"
CATEGORIES_TO_TRAIN = ["dog", "cat", "apple"]
TMP_GRAPH_OUTPUT_PATH = "/tmp/output_graph.pb"
TMP_LABELS_OUTPUT_PATH = "/tmp/output_labels.txt"
GRAPH_OUTPUT_PATH= "/home/playground/training/models/graph.pb"
LABELS_OUTPUT_PATH = "/home/playground/training/models/labels.txt"
MODEL_INFO_PATH  = "/home/playground/training/models/model_info.json"
TFRECORD_OUTPUT_PATH = "/home/playground/training/models/train.record"
LABELMAP_PATH = "/home/playground/training/models/label_map.pbtxt"

class RectAnnotation(object):
	def __init__(self, top, left, width, height):
		self._top = top
		self._left = left
		self._width = width
		self._height = height 

	@property
	def top(self):
		return self._top

	@property
	def left(self):
		return self._left

	@property
	def width(self):
		return self._width

	@property
	def height(self):
		return self._height




class Annotations(object):
	def __init__(self, annotations):
		self._current = 0
		self._annotations = []
		if annotations is not None:
			for annotation in annotations:
				a = RectAnnotation(annotation["top"], annotation["left"], annotation["width"], annotation["height"])
				self._annotations.append(a)
			

	@property
	def count(self):
		return len(self._annotations)

	def __iter__(self):
		return self

	def next(self): # Python 3: def __next__(self)
		if self._current >= len(self._annotations):
			raise StopIteration
		else:
			self._current += 1
			return self._annotations[(self._current - 1)]


class Donation(object):
	def __init__(self, filename, label):
		self._dir = None
		self._filename = filename
		self._img = None
		self._label = label
		self._annotations = None
		self._uuid = None

	def _open(self):
		if self._img == None:
			self._img = Image.open((self._dir + os.path.sep + self._filename) + ".jpg")
			return self._img
		return self._img
	@property
	def dir(self):
		return self._dir

	@dir.setter
	def dir(self, directory):
		self._dir = directory

	@property
	def uuid(self):
		return self._uuid

	@uuid.setter
	def uuid(self, uuid):
		self._uuid = uuid

	@property
	def size(self):
		self._open()
		return self._img.size

	@property
	def label(self):
		return self._label

	@label.setter
	def label(self, label):
		self._label = label

	@property
	def annotations(self):
		return self._annotations

	@annotations.setter
	def annotations(self, annotations):
		self._annotations = Annotations(annotations)

	@property
	def format(self):
		self._open()
		return self._img.format

	@property
	def filename(self):
		return self._filename

	@property
	def bytesIO(self):
		self._open()
		imgBytes = io.BytesIO()
		self._img.save(imgBytes, self.format)
		return imgBytes.getvalue()


def createTFExample(donation):

	imageFormat = ""
	if donation.format == 'JPEG':
		imageFormat = b'jpeg'
	elif donation.format == 'PNG':
		imageFormat = b'png'
	else:
		print 'Unknown Image format %s' %(donation.format,)
		return None

	width, height = donation.size
	filename = str(donation.filename)
	encodedImageData = donation.bytesIO

	xmins = []
	xmaxs = []
	ymins = []
	ymaxs = []

	for annotation in donation.annotations:
		xmins.append((annotation.left / width))
		xmaxs.append((annotation.left + annotation.width) / width)
		ymins.append((annotation.top / height))
		ymaxs.append((annotation.top + annotation.height) / height)

	label = [donation.label.encode('utf8')]
	classes = [(CATEGORIES_TO_TRAIN.index(donation.label) + 1)] #class indexes start with 1


	tf_example = tf.train.Example(features=tf.train.Features(feature={
      'image/height': dataset_util.int64_feature(height),
      'image/width': dataset_util.int64_feature(width),
      'image/filename': dataset_util.bytes_feature(filename),
      'image/source_id': dataset_util.bytes_feature(filename),
      'image/encoded': dataset_util.bytes_feature(encodedImageData),
      'image/format': dataset_util.bytes_feature(imageFormat),
      'image/object/bbox/xmin': dataset_util.float_list_feature(xmins),
      'image/object/bbox/xmax': dataset_util.float_list_feature(xmaxs),
      'image/object/bbox/ymin': dataset_util.float_list_feature(ymins),
      'image/object/bbox/ymax': dataset_util.float_list_feature(ymaxs),
      'image/object/class/text': dataset_util.bytes_list_feature(label),
      'image/object/class/label': dataset_util.int64_list_feature(classes),
  	}))
	return tf_example



def exportDonationsInCategory(name):
	donations = []
	url = BASEURL + "export?tags=" + name
	r = requests.get(url)
	if(r.status_code != 200):
		print "Couldn't get tags"
		return None
	data = r.json()
	for entry in data:
		if entry["probability"] < 0.8:
			continue
		d = Donation(entry["uuid"], name)
		d.uuid = entry["uuid"]
		d.annotations = entry["annotations"]
		donations.append(d)
	return donations

def cleanupTrainingDir():
	for f in os.listdir(CATEGORIES_DIR):
	    filePath = os.path.join(CATEGORIES_DIR, f)
	    try:
	        if os.path.isfile(filePath):
	            os.unlink(filePath)
	        elif os.path.isdir(filePath): shutil.rmtree(filePath)
	    except Exception as e:
	        print(e)
	        return False
	return True

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




def copyToTrainingDir(categoryName, donations):
	if os.path.exists(CATEGORIES_DIR + categoryName):
		print "Directory %s already exists!" %(categoryName,)
		return False
	os.makedirs(CATEGORIES_DIR + categoryName)
	if not os.path.exists(CATEGORIES_DIR + categoryName):
		print "Couldn't create directory %s!" %(categoryName,)
		return False

	for i in range(len(donations)):
		donation = donations[i]
		sourcePath = DONATIONS_DIR + donation.uuid
		destDir = CATEGORIES_DIR + categoryName + os.path.sep
		destPath = destDir + donation.uuid + ".jpg"
		
		#update directory in donation
		donation.dir = destDir
		donations[i] = donation
		
		shutil.copyfile(sourcePath, destPath)
	return True


def trainModel():
	cmd = ("python " + TENSORFLOW_DIR + "tensorflow" + os.path.sep + "examples" + os.path.sep + 
			"image_retraining" + os.path.sep + "retrain.py" + " --image_dir " + CATEGORIES_DIR + os.path.sep
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

def restartProcesses():
	p = subprocess.Popen("sudo supervisorctl restart all", stdout=subprocess.PIPE, shell=True)
	out, err = p.communicate()
	if p.returncode != 0:
		return False
	return True

def createTfRecordFile(donations):
	writer = tf.python_io.TFRecordWriter(TFRECORD_OUTPUT_PATH)
	for donation in donations:
		t = createTFExample(donation)
		writer.write(t.SerializeToString())

	writer.close()


def createLabelMap():
	try:
		f = open(LABELMAP_PATH, 'w+')
		cnt = 1
		for category in CATEGORIES_TO_TRAIN:
			entry = "item {\n\tid: " + str(cnt) + "\n\tname: " + category + "\n}\n\n"
			f.write(entry)
			cnt += 1
		f.close()
	except:
		print traceback.print_exc()
		return False
	return True
	



if __name__ == "__main__":
	if not cleanupTrainingDir():
		print "Couldn't cleanup training directory"
		sys.exit(1)

	for category in CATEGORIES_TO_TRAIN:
		donations = exportDonationsInCategory(category)
		if not copyToTrainingDir(category, donations):
			print "Couldn't copy data to training directory"
			sys.exit(1)

	createTfRecordFile(donations)

	if not createLabelMap():
		print "Couldn't create label map"
		sys.exit(1)


	# run: export PYTHONPATH="${PYTHONPATH}:/home/playground/tensorflow_models/research/:/home/playground/tensorflow_models/research/slim/"
	# python tensorflow_models/research/object_detection/train.py --pipeline_config_path=/home/playground/ssd_mobilenet_v1_imagemonkey.config --train_dir=/tmp
	# <- creates output in /tmp

	#TODO: adapt num_classes in ssd_mobilenet_v1_imagemonkey.config dynamically!!!!!

	#ERROR: might be related to the fact that we are not writing the classes right. (see line 180). we need to write class names according to the label mapping


	"""if not trainModel():
		print "Couldn't train model"
		sys.exit(1)

	if not writeModelInfo(CATEGORIES_TO_TRAIN):
		print "Couldn't write model info"
		sys.exit(1)

	print "Restarting processes..."
	if not restartProcesses():
		print "Couldn't restart processes"
		sys.exit(1)

	print "Successfully trained model"
	"""



	
	



