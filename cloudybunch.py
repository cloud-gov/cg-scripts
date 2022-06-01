#!/usr/bin/env python3

import random
import pprint

team = [
    ":andrew-burnes:",
    ":arsalan:",
    ":ben-berry:",
    ":mogul:",
    ":brian-hurst:",
    ":chiaka:",
    ":chris-mcgowan:",
    ":david-anderson:",
    ":david-corwin:",
    ":ephraim:",
    ":kelley:",
    ":markboyd:",
    ":markheadd:",
    ":melanie:",
    ":peterb:",
    ":rian-bogle:",
    ":robert-gottlieb:",
    ":shea:",
    ":van-nguyen:",
]

dict={}
for i in team:
    dict[i]=0

for n in range(1,24):
    bunch = random.sample(team,8)
    print(f':musical_note: {bunch[0]} {bunch[1]} {bunch[2]}\\n :blank: {bunch[3]} :cloud-gov: {bunch[4]} \\n :blank: {bunch[5]} {bunch[6]} {bunch[7]} :musical_note:')
    for m in range(0,7):
        dict[bunch[m]] = dict[bunch[m]] + 1


print("stats\n")
pp = pprint.PrettyPrinter(indent=4)
pp.pprint(dict)
