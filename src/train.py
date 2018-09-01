import docker
import argparse
import signal
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
		raven_client.captureException()
		return False

	if not restart_all_processes():
		log.info("Couldn't restart all processes")
		raven_client.captureMessage("Couldn't restart all processes!")
		return False

	log.info("Training done")
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

if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO) 

	parser = argparse.ArgumentParser(prog='PROG')
	parser.add_argument('--build_dir', help='specify the build directory', required=True)
	parser.add_argument('--clear_before_start', help='clear build directory before start', required=False, default=False)
	parser.add_argument('--dst_dir', help='specify the destination directory', required=True)
	parser.add_argument('--use_sentry', help='use sentry to log errors', required=False, default=False)
	parser.add_argument('--interval', help='rebuild interval [secs]', required=False, default=(3600 * 24)) #default is once per day

	args = parser.parse_args()

	if args.use_sentry:
		if not hasattr(secrets, 'SENTRY_DSN') or  secrets.SENTRY_DSN == "":
			log.error("Please provide a valid Sentry DSN!")
			sys.exit(1)

	raven_client = raven.Client(secrets.SENTRY_DSN)

	if not dir_exists(args.build_dir):
		log.error("Directory %s doesn't exist!" %(args.build_dir))
		sys.exit(1)

	categories = ["cat", "dog", "apple", "tree", "person"]


	while True:
		if not train_model(categories, args.build_dir, args.dst_dir, args.clear_before_start):
			time.sleep(3600 * 5) #in case of an error, wait five hours and try again
		else:
			time.sleep(args.interval) #if everything went fine, re-build after the specified interval


