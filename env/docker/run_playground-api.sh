#!/bin/bash

./api -use_sentry=$USE_SENTRY -redis_address=$REDIS_ADDRESS -donations_dir=/home/imagemonkey/data/donations/ -predictions_dir=/tmp/predictions -listen_port=$PLAYGROUND_API_PORT
