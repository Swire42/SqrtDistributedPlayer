#!/bin/bash

pkg install pulseaudio sox termux-api python
termux-setup-storage
pip install mutagen
echo alias sdp=\"cd $PWD \&\& python $PWD/sdp.py\" >> ~/.bashrc

echo '##### IMPORTANT #####'
echo 'Please make sure to have "Termux:API" installed (You can get it in Google Play)'
echo 'Please restart Termux. You will then be able to use "$ sdp" to run the player.'
echo '##### IMPORTANT #####'
