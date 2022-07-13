#!/usr/bin/env python3

import random

team = [
    ":andrew-burnes:",
    ":arsalan-haider:",
    ":mogul:",
    ":bhurst:",
    ":chiaka-opara:",
    ":chris-mcgowan:",
    ":david-anderson:",
    ":ephraim-gross:",
    ":kelley:",
    ":mark-boyd:",
    ":markheadd:",
    ":melanie:",
    ":peterb:",
    ":rian-bogle:",
    ":robert-gottlieb:",
    ":shea-bennett:",
    ":van-nguyen:",
]
# randomize the input list, t, 
# then print samples with spacing n
def bunch(t,n):
    bunch = random.sample(t,len(t))
    for n in range(0,len(t)+n,n):
        print(f':musical_note: {bunch[(n+0)%len(bunch)]} {bunch[(n+1)%len(bunch)]} {bunch[(n+2)%len(bunch)]}\\n',
            f' :blank: {bunch[(n+3)%len(bunch)]} :cloud-gov: {bunch[(n+4)%len(bunch)]} \\n',
            f' :blank: {bunch[(n+5)%len(bunch)]} {bunch[(n+6)%len(bunch)]} {bunch[(n+7)%len(bunch)]} :musical_note:')

bunch(team,2)
bunch(team,2)
