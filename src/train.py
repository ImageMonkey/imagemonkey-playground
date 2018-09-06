import docker
import argparse
import signal
import socket
import sys
import os
import shutil
import json
import datetime
import subprocess
import raven
import secrets
import logging
import time
from logging.handlers import RotatingFileHandler

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

container = None
raven_client = None

def signal_handler(sig, frame):
        log.info('You pressed Ctrl+C! - Stopping container')
        if container is not None:
        	container.stop()
        sys.exit(1)
signal.signal(signal.SIGINT, signal_handler)


def clear_dir(folder):
	for f in os.listdir(folder):
		file_path = os.path.join(folder, f)
		try:
			if os.path.isfile(file_path):
				os.unlink(file_path)
			elif os.path.isdir(file_path): 
				shutil.rmtree(file_path)
		except Exception as e:
			log.exception("Couldn't clear build directory")
			raven_client.captureException()
			return False
	return True

def is_dir_empty(path):
	if not os.listdir(path):
		return True
	return False

def dir_exists(path):
	if os.path.exists(path) and os.path.isdir(path):
		return True
	return False

def restart_all_processes():
	p = subprocess.Popen("sudo supervisorctl restart all", stdout=subprocess.PIPE, shell=True)
	out, err = p.communicate()
	if p.returncode != 0:
		return False
	return True

def read_trained_categories(path):
	content = None
	try:
		with open(path) as f:
			content = f.readlines()
		content = [x.strip() for x in content] 
	except Exception as e:
		log.exception("Couldn't read trained categories")
		raven_client.captureException()
	return content

def train_model(categories, build_dir, dst_dir, clear_before_start):
	log.info("Started training")

	if not clear_before_start:
		if not is_dir_empty(build_dir):
			log.error("Directory %s needs to be empty! Provide the --clear_before_start flag to clear it automatically.\nWARNING: ALL DATA WILL BE DELETED!" %(build_dir))
			raven_client.captureMessage("build directory needs to be empty!")
			return False
	else:
		if not clear_dir(build_dir):
			log.error("Couldn't remove directory %s" %(build_dir,))
			raven_client.captureMessage("Couldn't remove build directory!")
			return False

	#check again (just to be sure)
	if not is_dir_empty(build_dir):
		log.error("Directory %s needs to be empty! Provide the --clear_before_start flag to clear it automatically.\nWARNING: ALL DATA WILL BE DELETED!")
		raven_client.captureMessage("build directory needs to be empty!")
		return False

	client = docker.from_env()

	log.info("Pulling bbernhard/imagemonkey-train:latest")
	client.images.pull('bbernhard/imagemonkey-train:latest', stream=True)

	categories_str = "|".join(categories)

	cmd = "/home/imagemonkey/bin/monkey train --labels=\"" + categories_str + "\" --type=\"image-classification\""
	global container
	container = None
	container = client.containers.run("bbernhard/imagemonkey-train:latest", 
									  cmd, 
									  volumes={build_dir: {'bind': '/tmp', 'mode': 'rw'}},
									  user=1001,
									  detach=True)
	log.info("Starting Container")
	for line in container.logs(stream=True):
		log.debug(line.strip()) #in case you want to debug what's happening in the container, set loglevel to debug!



	p = build_dir + os.path.sep + "image_classification" + os.path.sep + "output" + os.path.sep + "labels.txt"
	categories = read_trained_categories(p) 
	if categories is None:
		log.error("Couldn't read trained categories from %s" %(p,))
		raven_client.captureMessage("Couldn't read trained categories!")
		return False

	if not write_model_info(categories, "inception-v3", (dst_dir + os.path.sep + "model_info.json")):
		log.error("Couldn't write model info to %s" %(dst_dir,))
		raven_client.captureMessage("Couldn't write model info!")
		return False


	
	try:
		#copy trained model to destination
		src = build_dir + os.path.sep + "image_classification" + os.path.sep + "output" + os.path.sep + "graph.pb"
		dst = dst_dir + os.path.sep + "graph.pb"
		shutil.copyfile(src, dst)

		#copy labels.txt to destination
		src = build_dir + os.path.sep + "image_classification" + os.path.sep + "output" + os.path.sep + "labels.txt"
		dst = dst_dir + os.path.sep + "labels.txt"
		shutil.copyfile(src, dst)

	except Exception as e:
		log.error("Couldn't copy trained model to destination")
		raven_client.captureException()
		return False

	if not restart_all_processes():
		log.info("Couldn't restart all processes")
		raven_client.captureMessage("Couldn't restart all processes!")
		return False

	log.info("Training done, stopping container")
	container.stop()
	return True


def write_model_info(categories, basedOn, path):
	data = {}
	now = datetime.datetime.now()

	try:
		if os.path.isfile(path):
			with open(path) as f:   
				data = json.load(f)
				data["build"] = data["build"] + 1
				data["created"] = now.strftime("%Y-%m-%d %H:%M")
				data["based_on"] = basedOn
				data["trained_on"] = categories
		else:
			data["build"] = 1
			data["created"] = now.strftime("%Y-%m-%d %H:%M")
			data["based_on"] = basedOn
			data["trained_on"] = categories
		with open(path, 'w') as outfile:
			json.dump(data, outfile)
	except Exception as e:
		log.exception("Couldn't write model info")
		raven_client.captureException()
		return False
	return True

#we are using abstract sockets to make sure that only one instance of this
#program runs at any time. abstract sockets are better, as they are no lingering
#files in case the program dies
def acquire_lock(process_name):
    # Without holding a reference to our socket somewhere it gets garbage
    # collected when the function exits
    acquire_lock._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    try:
        acquire_lock._lock_socket.bind('\0' + process_name)
        #print("got the lock") #got the lock
    except socket.error:
        log.info("Couldn't start program, as there is already one instance of this program running")
        raven_client.captureMessage("Couldn't start program, as there is already one instance of this program running")
        sys.exit()

if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO) 

	parser = argparse.ArgumentParser(prog='PROG')
	parser.add_argument('--build_dir', help='specify the build directory', required=True)
	parser.add_argument('--clear_before_start', help='clear build directory before start', type=bool, required=False, default=False)
	parser.add_argument('--dst_dir', help='specify the destination directory', required=True)
	parser.add_argument('--use_sentry', help='use sentry to log errors', type=bool, required=False, default=False)
	parser.add_argument('--log_folder', help='log folder', required=False, default="")
	#parser.add_argument('--interval', help='rebuild interval [secs]', type=int, required=False, default=(3600 * 24)) #default is once per day

	args = parser.parse_args()

	if args.log_folder != "":
		log_folder = args.log_folder + os.path.sep + "out.log"
		handler = RotatingFileHandler(log_folder, maxBytes=25000, backupCount=5)
		log.addHandler(handler)

	#make sure that only one instance of this script runs at any time
	acquire_lock("imagemonkey-playground-train")

	if args.use_sentry:
		if not hasattr(secrets, 'SENTRY_DSN') or  secrets.SENTRY_DSN == "":
			log.error("Please provide a valid Sentry DSN!")
			sys.exit(1)

	raven_client = raven.Client(secrets.SENTRY_DSN)
	raven_client.captureMessage("Starting ImageMonkey Train")
	log.info("Starting ImageMonkey Train")

	if not dir_exists(args.build_dir):
		log.error("Directory %s doesn't exist!" %(args.build_dir))
		sys.exit(1)

	categories = ["cat", "dog", "apple", "tree", "person"]

	success = False
	try:
		success = train_model(categories, args.build_dir, args.dst_dir, args.clear_before_start)
	except Exception as e:
		log.exception("Couldn't train neural net due to uncaught exception")
		raven_client.captureException()

	if not success:
		log.error("Couldn't train neural net")
	else:
		log.info("Successfully trained neural net")


	"""while True:
		success = False
		try:
			success = train_model(categories, args.build_dir, args.dst_dir, args.clear_before_start)
		except Exception as e:
			log.exception("Couldn't train neural net due to uncaught exception")
			raven_client.captureException()

		if not success:
			log.info("Couldn't train neural net, re-try in %d" %(args.interval,))
			time.sleep(3600 * 5) #in case of an error, wait five hours and try again
		else:
			log.info("Successfully trained neural net, rebuild in %d" %(args.interval,))
			time.sleep(args.interval) #if everything went fine, re-build after the specified interval"""


