#!/usr/bin/env bash

#this actually needs to happen after compiling
echo "Copying data into the container!"
cp -r Server/data . #where does it need to end up?
cp -r Server/hasura-metadata . #where does it need to end up?

#this needs to happen before compiling
cp ../everest-demo/citrineos/Dockerfile Server/Dockerfile
