#!/bin/bash

/usr/bin/wait-for-it.sh 127.0.0.1:$REDIS_PORT -- echo "Redis (127.0.0.1:$REDIS_PORT) is up"

./predict -redis-address=$REDIS_ADDRESS 
