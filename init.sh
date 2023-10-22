#!/bin/sh

git clone https://github.com/yarrm80s/orpheusdl.git
pip install -r orpheusdl/requirements.txt
git clone https://github.com/uhwot/orpheusdl-deezer orpheusdl/modules/deezer
mkdir orpheusdl/config
cp settings.json orpheusdl/config/settings.json
pip install -r requirements.txt