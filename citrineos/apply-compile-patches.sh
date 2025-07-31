#!/usr/bin/env bash

# This is a patch to the source code, so we need to apply it
# before we build.
# And there is no harm in turning off OCSP completely

echo "Copying data into the container!"
cp -r Server/data . #where does it need to end up?
cp -r Server/hasura-metadata . #where does it need to end up?

ls
pwd
cp Dockerfile Server/Dockerfile
