#!/usr/bin/env python3

import random

team = [
    ":amir:",
    ":david-corwin:",
    ":ben-berry:",
    ":peterb:",
    ":andrew-burnes:",
    ":van-nguyen:",
    ":chris-mcgowan:",
    ":kelley:",
    ":markheadd:",
    ":lindsay:",
    ":melanie:",
    ":gerald:",
    ":rian-bogle:"
]

for n in range(1,24):
    bunch = random.sample(team,8)
    print(f':musical_note: {bunch[0]} {bunch[1]} {bunch[2]}\\n :blank: {bunch[3]} :cloud-gov: {bunch[4]} \\n :blank: {bunch[5]} {bunch[6]} {bunch[7]} :musical_note:')
