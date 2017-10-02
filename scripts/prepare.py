#!/usr/bin python 
import os
import requests
import shutil
import subprocess

BASEURL = "https://api.imagemonkey.io/v1/"
DONATIONS_DIR = "/home/playground/donations/"
CATEGORIES_DIR = "/home/playground/training/categories/"
TENSORFLOW_DIR = "/home/playground/tensorflow/"
CATEGORIES_TO_TRAIN = ["dog", "cat", "apple"]
TMP_GRAPH_OUTPUT_DIR = "/tmp/output_graph.pb"
TMP_LABELS_OUTPUT_DIR = "/tmp/output_labels.txt"
GRAPH_OUTPUT_DIR = "/home/playground/training/models/graph.pb"
LABELS_OUTPUT_DIR = "/home/playground/training/models/labels.txt"


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


def copyToTrainingDir(categoryName, uuids):
	if os.path.exists(CATEGORIES_DIR + categoryName):
		print "Directory %s already exists!" %(categoryName,)
		return
	os.makedirs(CATEGORIES_DIR + categoryName)
	if not os.path.exists(CATEGORIES_DIR + categoryName):
		print "Couldn't create directory %s!" %(categoryName,)
		return

	for uuid in uuids:
		sourcePath = DONATIONS_DIR + uuid
		destPath = CATEGORIES_DIR + categoryName + os.path.sep + uuid + ".jpg"
		shutil.copyfile(sourcePath, destPath)


def trainModel():
	cmd = ("python " + TENSORFLOW_DIR + "tensorflow" + os.path.sep + "examples" + os.path.sep + 
			"image_retraining" + os.path.sep + "retrain.py" + " --image_dir " + CATEGORIES_DIR + os.path.sep
			+ " --output_graph " + TMP_GRAPH_OUTPUT_DIR + " --output_labels " + TMP_LABELS_OUTPUT_DIR)
	 
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
	out, err = p.communicate()
	if p.returncode != 0:
		print "Couldn't retrain model!"
	else: #model creation successful
		shutil.copyfile(TMP_GRAPH_OUTPUT_DIR, GRAPH_OUTPUT_DIR) 
		shutil.copyfile(TMP_LABELS_OUTPUT_DIR, LABELS_OUTPUT_DIR)



if __name__ == "__main__":
	cleanupTrainingDir()

	for category in CATEGORIES_TO_TRAIN:
		uuids = exportUuidsFromCategory(category)
		copyToTrainingDir(category, uuids)

	trainModel()

	
	



