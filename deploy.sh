#!/bin/bash
VERSION=${1:-v2}
docker build  .  -t aolifu/awalong2:$VERSION
docker push aolifu/awalong2:$VERSION
docker stop awalong2
docker rm awalong2
docker run -d --name awalong2 -p 11015:5001 aolifu/awalong2:$VERSION