import redis
import cv2 as cv
import numpy as np
import uuid
import json
import base64
import time

from PIL import Image
import StringIO


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
    """cnt = contours[0]
    max_area = cv.contourArea(cnt)

    for cont in contours:
        if cv.contourArea(cont) > max_area:
            cnt = cont
            max_area = cv.contourArea(cont)

    epsilon = 0.009*cv.arcLength(cnt,True)
    approx = cv.approxPolyDP(cnt,epsilon,True)

    contours = cv.convexHull(cnt)"""

    if len(contours) == 0:
        contours = np.empty([0, 0])
    else:
        contours = np.vstack(contours).squeeze()
        for elem in contours:
            elem[0] = elem[0] * float(scaleX)
            elem[1] = elem[1] * float(scaleY)

    return contours, None




if __name__ == "__main__":
    pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)

    expireInSecs = 600
    while True:
        obj = r.blpop("grabcutme")
        jsonObj = json.loads(obj[1])
        key = "grabcut" + jsonObj["uuid"]
        err = None
        
        try:
            imgBytes = base64.b64decode(jsonObj["mask"])
            arr = np.fromstring(imgBytes, np.uint8)
            mask = cv.imdecode(arr, 0) 
        except:
            err = "Couldn't decode image"

        if err is None:
            try:
                cont, err = getContours(jsonObj["filename"], mask)
            except:
                err = "Couldn't process request"

        res = {}
        res["error"] = ""
        if err is not None:
            res["error"] = err

        if err is None:
            res["points"] = cont.tolist()
        else:
            res["points"] = np.empty([0, 0])
            
        r.setex(key, json.dumps(res), expireInSecs)
