#!/bin/bash

/usr/bin/wait-for-it.sh 127.0.0.1:$REDIS_PORT -- echo "Redis (127.0.0.1:$REDIS_PORT) is up"


echo "Starting tests (after 10 sec delay)"
sleep 10

./test -test.v -test.parallel 1 -test.timeout=600m
retVal=$?
if [ $retVal -ne 0 ]; then
	echo "Aborting due to error"
	exit $retVal
fi
