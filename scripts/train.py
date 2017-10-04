#!/usr/bin python 
import os
import requests
import shutil
import subprocess
import datetime
import json
import traceback
import sys

BASEURL = "https://api.imagemonkey.io/v1/"
DONATIONS_DIR = "/home/playground/donations/"
CATEGORIES_DIR = "/home/playground/training/categories/"
TENSORFLOW_DIR = "/home/playground/tensorflow/"
CATEGORIES_TO_TRAIN = ["dog", "cat", "apple"]
TMP_GRAPH_OUTPUT_PATH = "/tmp/output_graph.pb"
TMP_LABELS_OUTPUT_PATH = "/tmp/output_labels.txt"
GRAPH_OUTPUT_PATH= "/home/playground/training/models/graph.pb"
LABELS_OUTPUT_PATH = "/home/playground/training/models/labels.txt"
MODEL_INFO_PATH  = "/home/playground/training/models/model_info.json"


def exportUuidsFromCategory(name):
	uuids = []
	url = BASEURL + "export?tags=" + name
	r = requests.get(url)
	if(r.status_code != 200):
		print "Couldn't get tags"
		return None
	data = r.json()
	for entry in data:
		if entry["probability"] < 0.8:
			continue
		uuids.append(entry["uuid"])
	return uuids

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




def copyToTrainingDir(categoryName, uuids):
	if os.path.exists(CATEGORIES_DIR + categoryName):
		print "Directory %s already exists!" %(categoryName,)
		return False
	os.makedirs(CATEGORIES_DIR + categoryName)
	if not os.path.exists(CATEGORIES_DIR + categoryName):
		print "Couldn't create directory %s!" %(categoryName,)
		return False

	for uuid in uuids:
		sourcePath = DONATIONS_DIR + uuid
		destPath = CATEGORIES_DIR + categoryName + os.path.sep + uuid + ".jpg"
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

if __name__ == "__main__":
	if not cleanupTrainingDir():
		print "Couldn't cleanup training directory"
		sys.exit(1)

	for category in CATEGORIES_TO_TRAIN:
		uuids = exportUuidsFromCategory(category)
		if not copyToTrainingDir(category, uuids):
			print "Couldn't copy data to training directory"
			sys.exit(1)

	if not trainModel():
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



	
	



