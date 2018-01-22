import sys
import os

#add Mask_RCNN path to search path
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + os.path.sep + ".." + os.path.sep + "Mask_RCNN")

import requests
import secrets
import time
import coco
import utils
import model as modellib
import skimage.io
import json
import cv2
import argparse
import numpy as np
import time

class InferenceConfig(coco.CocoConfig):
    # Set batch size to 1 since we'll be running inference on
    # one image at a time. Batch size = GPU_COUNT * IMAGES_PER_GPU
    GPU_COUNT = 1
    IMAGES_PER_GPU = 1


availableTrainedLabels = ['BG', 'person', 'bicycle', 'car', 'motorcycle', 'airplane',
			               'bus', 'train', 'truck', 'boat', 'traffic light',
			               'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird',
			               'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear',
			               'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie',
			               'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
			               'kite', 'baseball bat', 'baseball glove', 'skateboard',
			               'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
			               'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
			               'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
			               'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed',
			               'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
			               'keyboard', 'cell phone', 'microwave', 'oven', 'toaster',
			               'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors',
			               'teddy bear', 'hair drier', 'toothbrush']


class LocalObjStorage(object):
	def __init__(self, path):
		self._path = path

	def save(obj):
		with open(self._path, 'wb') as f:
			pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

	def load():
		with open(self._path, 'rb') as f:
			return pickle.load(f) 


def isLabelDefined(labels, label):
	for elem in labels:
		if elem == label:
			return True
	return False


class AutoAnnotator(object):
	def __init__(self, apiBaseUrl, donationsDir, cocoModelDir):
		self._availableLabelsUrl = apiBaseUrl + "/v1/label"
		self._getImgUrl = apiBaseUrl + "/v1/internal/auto-annotation"
		self._addAnnotationUrl = apiBaseUrl + "/v1/internal/auto-annotate" 

		self._headers = headers = {"X-Client-Id": secrets.X_CLIENT_ID, "X-Client-Secret": secrets.X_CLIENT_SECRET}

		self._availableLabels = None
		self._getAvailableLabels()

		self._itemsToProcess = self._getItemsToProcess()
		self._currentProcessedItem = -1

		cocoModelPath = os.path.join(cocoModelDir, "mask_rcnn_coco.h5")

		config = InferenceConfig()

		# Create model object in inference mode.
		self._model = modellib.MaskRCNN(mode="inference", model_dir=cocoModelDir, config=config)

		self._donationsDir = os.path.abspath(donationsDir)

		# Load weights trained on MS-COCO
		self._model.load_weights(cocoModelPath, by_name=True)

	def _getAvailableLabels(self):
		r = requests.get(self._availableLabelsUrl)
		if r.status_code == 200:
			self._availableLabels = r.json()

	def _getItemsToProcess(self):
		labels = ""
		for elem in availableTrainedLabels:
			labels += (elem + ",")

		params = {"label": labels}
		r = requests.get(self._getImgUrl, params=params, headers=self._headers)
		if r.status_code != 200:
			print("[Auto Annotator] Couldn't fetch next image")
			return None
		return r.json()



	def next(self):
		self._currentProcessedItem += 1
		if ((self._itemsToProcess is not None) and (self._currentProcessedItem < len(self._itemsToProcess))):
			data = self._itemsToProcess[self._currentProcessedItem]
			imageId = data["image"]["uuid"]
			imgPath = os.path.join(self._donationsDir, imageId)
			image = skimage.io.imread(imgPath)

			print("[Auto Annotator] Processing Image ", imageId)

			results = self._model.detect([image], verbose=1)
			self._save(data, results)
			return True
		else:
			return False


	def _getOuterContourFromMask(self, mask):
		points = []
		_, contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
		if len(contours) == 0:
			contours = np.empty([0, 0])
		else:
			contours = np.vstack(contours).squeeze()
		
		for elem in contours:
			points.append({"x": elem[0].item(), "y": elem[1].item()})

		return points

	def _masksToAnnotations(self, masks):
		annotations = []
		for mask in masks:
			points = self._getOuterContourFromMask(mask)
			annotations.append({"type": "polygon", "points": points, "angle": 0})
		return annotations



	def _addAnnotation(self, imageId, label, masks):
		url = self._addAnnotationUrl + "/" + imageId
		data = {}
		data["label"] = label
		data["sublabel"] = ""
		data["annotations"] = self._masksToAnnotations(masks)

		r = requests.post(url, json=data, headers=self._headers)
		if r.status_code != 201:
			print("[Auto Annotator] Couldn't save annotation for image ", imageId)


	def _save(self, data, results):
		r = results[0]
		imageId = data["image"]["uuid"]
		boxes = r["rois"]
		masks = r["masks"]
		classIds = r["class_ids"]
		scores = r["scores"]

		N = boxes.shape[0]
		if not N:
			print("[Auto Annotator] no instances to process")
			return
		else:
			assert boxes.shape[0] == masks.shape[-1] == classIds.shape[0]

		#group masks by label
		groupedMasks = {}
		for i in range(N):
			mask = masks[:, :, i]
			classId = classIds[i]
			score = scores[i] if scores is not None else None
			label = availableTrainedLabels[classId]

			try:
				existingMasks = groupedMasks[label]
				existingMasks.append(mask)
				groupedMasks[label] = existingMasks
			except KeyError:
				groupedMasks[label] = [mask]

		if len(groupedMasks) > 0:
			for key in groupedMasks:
				if isLabelDefined(data["labels"], key):
					if((score is not None) and (score > 0.55)):
						self._addAnnotation(imageId, key, groupedMasks[key])
					else:
						print("label score too low, so skipping it", key)
				else:
					print("label not defined, so skipping it ", key)
		else: #nothing found
			pass




if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Auto Annotator (uses Mask R-CNN)')
	parser.add_argument('--api-baseurl', dest='apibaseurl', type=str, help='ImageMonkey API URL', default='http://127.0.0.1:8081')
	parser.add_argument('--donations-dir', dest='donationsdir', type=str, help='path to the donations directory', default='../../imagemonkey-core/donations/')
	parser.add_argument('--coco-model-dir', dest='cocomodeldir', type=str, help='path to the COCO model directory', default='../models/coco/')
	#parser.add_argument('--exceptionslist', dest='exceptionslist', type=str, help='path to the exceptions file', default='')

	args = parser.parse_args()

	autoAnnotator = AutoAnnotator(args.apibaseurl, args.donationsdir, args.cocomodeldir)


	while True:
		try:
			if not autoAnnotator.next(): #everything annotated
				time.sleep(60 * 5) #sleep for 5min
				break
		except:
			pass #TODO: handle me
		time.sleep(30)


	
    
        