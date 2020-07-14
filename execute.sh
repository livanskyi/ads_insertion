#!/bin/bash

cd ..
mkdir -p data

cd movie-ads-creator || exit

sudo apt-get remove docker docker-engine docker.io containerd runc

sudo apt-get update

sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

sudo apt-get update

sudo apt-get install docker-ce docker-ce-cli containerd.io

if [ -z "$(sudo docker images -q movie_creator:1.0)" ]
then
sudo docker build -t movie_creator:1.0 .
fi

cd ..

sudo docker run -d -p 80:80 -it --name dock --mount type=bind,source="$(pwd)"/data,target=/app/output movie_creator:1.0
sudo docker container stop dock
