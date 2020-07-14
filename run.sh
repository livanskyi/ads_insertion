#!/bin/bash

sudo docker container start dock
sudo docker logs -f --tail=500 dock > ../data/log_file.log