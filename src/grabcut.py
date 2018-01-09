import redis
import cv2 as cv
import numpy as np
import uuid
import json
import base64
import time

from PIL import Image
import StringIO

"""#rect = (0,0,1,1)
BLUE = [255,0,0]   
#FILENAME = "C:\\Users\\Bernhard\\Pictures\\hund-garten-terrasse.jpg"


class Rect(object):
    def __init__(self, left, top, width, height):
        self._left = left
        self._top = top
        self._width = width
        self._height = height

    @property
    def left(self):
        return self._left

    @property
    def top(self):
        return self._top

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self.height

    @property
    def x1(self):
        return self._left   

    @property
    def y1(self):
        return self._top

    @property
    def x2(self):
        return self._left + self._width 

    @property
    def y2(self):
        return self._top + self._height


class Bg(object):
    def __init__(self, data):
        self._data = data

    @property
    def data(self):
        return self._data

class Fg(object):
    def __init__(self, data):
        self._data = data

    @property
    def data(self):
        return self._data


def getContours(filename, rect):
    img = cv.imread(filename)
    img2 = img.copy() 
    mask = np.zeros(img.shape[:2], dtype = np.uint8) # mask initialized to PR_BG
    output = np.zeros(img.shape,np.uint8)           # output image to be shown

    cv.rectangle(img, (rect.x1, rect.y1) ,(rect.x2, rect.y2), BLUE, 2)
    rect = (min(rect.x1, rect.x2), min(rect.y1, rect.y2), abs(rect.x1 - rect.x2), abs(rect.y1 - rect.y2))

    bgdmodel = np.zeros((1,65),np.float64)
    fgdmodel = np.zeros((1,65),np.float64)
    cv.grabCut(img2,mask,rect,bgdmodel,fgdmodel,1,cv.GC_INIT_WITH_RECT)

    mask2 = np.where((mask==1) + (mask==3),255,0).astype('uint8')
    #output = cv.bitwise_and(img2,img2,mask=mask2)


    _, contours, _ = cv.findContours(mask2, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    #find the biggest area
    cnt = contours[0]
    max_area = cv.contourArea(cnt)

    for cont in contours:
        if cv.contourArea(cont) > max_area:
            cnt = cont
            max_area = cv.contourArea(cont)

    epsilon = 0.009*cv.arcLength(cnt,True)
    approx = cv.approxPolyDP(cnt,epsilon,True)

    contours = cv.convexHull(cnt)


    #print contours
    if len(contours) == 0:
        contours = np.empty([0, 0])
    else:
        contours = np.vstack(contours).squeeze()

    return contours"""


"""def getContours(filename, contoursImg):
    #mask = np.zeros(img.shape[:2],np.uint8)
    bgdModel = np.zeros((1,65),np.float64)
    fgdModel = np.zeros((1,65),np.float64)

    grabcutMask = cv.imread('C:\\imagemonkey-playground\\predictions\\test.png', 0) #load mask picture
    img = cv.imread(filename)
    img = cv.resize(img, (grabcutMask.shape[:2][1], grabcutMask.shape[:2][0]))
    print img.shape[:2]
    print grabcutMask.shape[:2]
    img2 = img.copy()

    mask = np.zeros(img.shape[:2],np.uint8)

    #red = 147
    #green = 200
    #blue = 95

    #mask[np.where(grabcutMask == 0)] = cv.GC_BGD #sure background
    #mask[np.where(grabcutMask == 76)] = cv.GC_FGD #sure foreground
    #mask[np.where(grabcutMask == 200)] = cv.GC_PR_FGD #probable foreground
    #mask[np.where(grabcutMask == 95)] = cv.GC_PR_BGD #probable background

    mask[np.where(grabcutMask == 0)] = cv.GC_BGD #sure background
    mask[np.where(grabcutMask == 255)] = cv.GC_PR_FGD #probable foreground

    mask, bgdModel, fgdModel = cv.grabCut(img,mask,None,bgdModel,fgdModel,5,cv.GC_INIT_WITH_MASK)
    mask2 = np.where((mask==1) + (mask==3),255,0).astype('uint8')
    output = cv.bitwise_and(img,img,mask=mask2)


    _, contours, _ = cv.findContours(mask2, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    #find the biggest area
    cnt = contours[0]
    max_area = cv.contourArea(cnt)

    for cont in contours:
        if cv.contourArea(cont) > max_area:
            cnt = cont
            max_area = cv.contourArea(cont)

    epsilon = 0.009*cv.arcLength(cnt,True)
    approx = cv.approxPolyDP(cnt,epsilon,True)

    contours = cv.convexHull(cnt)
    hull = cv.convexHull(cnt)

    cv.drawContours(img, [hull], -1, (255, 255, 255), 2)


    #mask2 = np.where((mask==2)|(mask==0),0,1).astype('uint8')
    #img3 = img2*mask2[:,:,np.newaxis]
    #mask = np.where((mask==2)|(mask==0),0,1).astype('uint8')
    #output = cv.bitwise_and(img3,img3,mask=mask2)

    cv.imshow('output', output)
    cv.imshow('input', img)
    while True:
        k = cv.waitKey(1)

    #mask.create(newmask.size(), cv.CV_8UC1);  #CV_8UC1 is single channel


    # newmask is the mask image I manually labelled
    #newmask = cv.imread('C:\\imagemonkey-playground\\predictions\\test.png', 0)

    #print newmask != 0
    # whereever it is marked white (sure foreground), change mask=1
    # whereever it is marked black (sure background), change mask=0
    #mask[newmask == 0] = 0
    #mask[newmask == 255] = 1
    #mask, bgdModel, fgdModel = cv.grabCut(img,mask,None,bgdModel,fgdModel,5,cv.GC_INIT_WITH_MASK)
    #mask = np.where((mask==2)|(mask==0),0,1).astype('uint8')"""


def getContours(filename, grabcutMask):
    bgdModel = np.zeros((1,65),np.float64)
    fgdModel = np.zeros((1,65),np.float64)

    img = cv.imread(filename)

    grabcutMaskShape = grabcutMask.shape[:2]
    imgShape = img.shape[:2]

    if((grabcutMaskShape[0] > imgShape[0]) or (grabcutMaskShape[1] > imgShape[1])):
        return np.empty([0, 0]), "mask cannot be bigger than image!"

    oldImgSize = img.shape[:2]
    img = cv.resize(img, (grabcutMask.shape[:2][1], grabcutMask.shape[:2][0]))
    newImgSize = img.shape[:2]

    scaleX = float(oldImgSize[1]) / newImgSize[1]
    scaleY = float(oldImgSize[0]) / newImgSize[0]

    mask = np.zeros(img.shape[:2],np.uint8)

    mask[np.where((grabcutMask != 0) & (grabcutMask != 255))] = cv.GC_PR_FGD #probable foreground
    mask[np.where(grabcutMask == 0)] = cv.GC_BGD #sure background
    mask[np.where(grabcutMask == 255)] = cv.GC_FGD #sure foreground


    cv.grabCut(img, mask, None, bgdModel, fgdModel, 5, cv.GC_INIT_WITH_MASK)
    mask2 = np.where((mask==1) + (mask==3),255,0).astype('uint8')

    _, contours, _ = cv.findContours(mask2, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    #find the biggest area
    cnt = contours[0]
    max_area = cv.contourArea(cnt)

    for cont in contours:
        if cv.contourArea(cont) > max_area:
            cnt = cont
            max_area = cv.contourArea(cont)

    epsilon = 0.009*cv.arcLength(cnt,True)
    approx = cv.approxPolyDP(cnt,epsilon,True)

    contours = cv.convexHull(cnt)

    if len(contours) == 0:
        contours = np.empty([0, 0])
    else:
        contours = np.vstack(contours).squeeze()
        for elem in contours:
            elem[0] = elem[0] * float(scaleX)
            elem[1] = elem[1] * float(scaleY)

    print "done"
    return contours, None




if __name__ == "__main__":
    pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)

    expireInSecs = 600
    while True:
        obj = r.blpop("grabcutme")
        jsonObj = json.loads(obj[1])
        key = "grabcut" + jsonObj["uuid"]

        imgBytes = base64.b64decode(jsonObj["mask"])
        arr = np.fromstring(imgBytes, np.uint8)
        mask = cv.imdecode(arr, 0) 
        cont, err = getContours(jsonObj["filename"], mask)

        res = {}
        res["error"] = ""
        if err is not None:
            res["error"] = err
        res["points"] = cont.tolist()
            
        r.setex(key, json.dumps(res), expireInSecs)
