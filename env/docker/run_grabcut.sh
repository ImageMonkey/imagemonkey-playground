#!/bin/bash

/usr/bin/wait-for-it.sh 127.0.0.1:$REDIS_PORT -- echo "Redis (127.0.0.1:$REDIS_PORT) is up"


python3 -u /tmp/grabcut/grabcut.py --redis_port $REDIS_PORT --use_sentry $USE_SENTRY
