import redis
import cv2 as cv
import numpy as np
import json
import base64
import time
from sentry_sdk import init, capture_exception, capture_message
import argparse
import sys
import os

def get_contours(filename, grabcut_mask):
    bgd_model = np.zeros((1,65),np.float64)
    fgd_model = np.zeros((1,65),np.float64)

    img = cv.imread(filename)

    grabcut_mask_shape = grabcut_mask.shape[:2]
    img_shape = img.shape[:2]

    if((grabcut_mask_shape[0] > img_shape[0]) or (grabcut_mask_shape[1] > img_shape[1])):
        return np.empty([0, 0]), "mask cannot be bigger than image!"

    old_img_size = img.shape[:2]
    img = cv.resize(img, (grabcut_mask.shape[:2][1], grabcut_mask.shape[:2][0]))
    new_img_size = img.shape[:2]

    scale_x = float(old_img_size[1]) / new_img_size[1]
    scale_y = float(old_img_size[0]) / new_img_size[0]

    mask = np.zeros(img.shape[:2],np.uint8)

    mask[np.where((grabcut_mask != 0) & (grabcut_mask != 255))] = cv.GC_PR_FGD #probable foreground
    mask[np.where(grabcut_mask == 0)] = cv.GC_BGD #sure background
    mask[np.where(grabcut_mask == 255)] = cv.GC_FGD #sure foreground


    cv.grabCut(img, mask, None, bgd_model, fgd_model, 5, cv.GC_INIT_WITH_MASK)
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
            elem[0] = elem[0] * float(scale_x)
            elem[1] = elem[1] * float(scale_y)

    return contours, None


def is_maintenance(file_path):
    if file_path is not None:
        if os.path.exists(file_path):
            return True
    return False



if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='PROG')
    parser.add_argument('--use_sentry', help='use sentry to log errors', type=str, required=False, default="false")
    parser.add_argument('--maintenance_file', help='path to the maintenance file', required=False, default=None)
    parser.add_argument('--redis_port', help='Redis port', type=int, required=False, default=6379)

    args = parser.parse_args()

    if args.use_sentry != "false" and args.use_sentry != "true":
        print("--use_sentry needs to be true or false!")
        sys.exit(1)

    if args.use_sentry == "true":
        sentry_dsn = os.environ.get("SENTRY_DSN")
        if sentry_dsn is None:
            print("Please provide a valid Sentry DSN!")
            sys.exit(1)
        init(sentry_dsn)
    else:
        init("")


    if not is_maintenance(args.maintenance_file):
        capture_message("Starting ImageMonkey Grabcut")
        print("Starting ImageMonkey Grabcut")

        pool = redis.ConnectionPool(host='localhost', port=str(args.redis_port), db=0)
        r = redis.Redis(connection_pool=pool)

        expire_in_secs = 600
        while True:
            obj = r.blpop("grabcutme")
            json_obj = json.loads(obj[1])
            key = "grabcut" + json_obj["uuid"]
            err = None
            
            try:
                img_bytes = base64.b64decode(json_obj["mask"])
                arr = np.fromstring(img_bytes, np.uint8)
                mask = cv.imdecode(arr, 0) 
            except Exception as e:
                capture_exception()
                err = "Couldn't decode image"

            if err is None:
                try:
                    cont, err = get_contours(json_obj["filename"], mask)
                except Exception as e:
                    capture_exception()
                    err = "Couldn't process request"

            res = {}
            res["error"] = ""
            if err is not None:
                res["error"] = err

            if err is None:
                res["points"] = cont.tolist()
            else:
                res["points"] = np.empty([0, 0]).tolist()
                
            r.setex(key, json.dumps(res), expire_in_secs)
    else:
        print("Starting ImageMonkey Grabcut (Maintenance Mode)")
        while True:
            time.sleep(1)
