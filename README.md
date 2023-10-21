# Bandeco Unicamp Bot

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](./LICENSE)

To run the bot yourself, you will need: 
- Python3 and pip (tested with 3.10)

## Setup for local run
- Install gl libs `apt-get update && apt-get install libgl1-mesa-glx -y`
- Upgrade pip3 `pip3 install --upgrade pip`
- Install virtualenv `python3 -m pip install --user virtualenv`
- Creating a virtual environment `python3 -m venv env`
- Activating a virtual environment `source env/bin/activate`
- Install Python Package Index (PyPI) `pip3 install requests`
- Install requirements: `pip3 install -r requirements.txt`
- Then run the bot with `python3 scr/bot.py`

## Setup for docker run
- Install docker `apt-get update && apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin`
- Docker Portainer create `docker volume create portainer_data`
- Docker Portainer run `docker run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:latest`
- Docker bandeco build `docker build -t bot/bandeco .`
- Docker bandeco run `docker run -d -p 5000:5000 --name=bandeco --restart=always --env-file=.env bot/bandeco:latest`

Note that you need to set the environment variables for the local run and the docker run.

Code documentation is minimal but there.