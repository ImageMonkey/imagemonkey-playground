#!/bin/bash

/usr/bin/wait-for-it.sh 127.0.0.1:$REDIS_PORT -- echo "Redis (127.0.0.1:$REDIS_PORT) is up"

./api -use_sentry=$USE_SENTRY -redis_address=$REDIS_ADDRESS -donations_dir=/home/imagemonkey-playground/donations/ -predictions_dir=/tmp/predictions/ -listen_port=$PLAYGROUND_API_PORT
