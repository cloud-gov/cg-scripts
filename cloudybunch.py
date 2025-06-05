#!/usr/bin/env python3

import random

# Need emoji:
#   Anna
#   Banessa
#   Weibel
#   Jason
#   Joe
#   Katherine
#   Kudeha
#   Nicole
#   Sean
#   William
#   Zachary
#   --
#   Cathy
#   Marjorie
#   David K
#   David S
#   Arantxa

team = [
    ":andrew-burnes:",
    ":annep:",
    ":arsalan-haider:",
    ":bhurst:",
    ":carlo:",
    ":chris-mcgowan:",
    ":david-anderson:",
    ":eleni:",
    ":ephraim-gross:",
    ":james-hochadel:",
    ":kelsey-foley:",
    ":mark-boyd:",
    ":matt-henry:",
    ":pauldoomgov:",
    ":peterb:",
    ":robert-gottlieb:",
    ":ryanahearn:",
    ":sarah-rudder:",
    ":steve-greenberg:",
    ":sven:",
    ":van-nguyen:",
    ":yuda:"
]
# randomize the input list, t,
# then print samples with spacing n
def bunch(t,n):
    bunch = random.sample(t,len(t))
    for n in range(0,len(t)+n,n):
        print(f':musical_note:{bunch[(n+0)%len(bunch)]}{bunch[(n+1)%len(bunch)]}{bunch[(n+2)%len(bunch)]}\\n'
            f':blank:{bunch[(n+3)%len(bunch)]}:cloud-gov:{bunch[(n+4)%len(bunch)]}\\n'
            f':blank:{bunch[(n+5)%len(bunch)]}{bunch[(n+6)%len(bunch)]}{bunch[(n+7)%len(bunch)]}:musical_note:')

bunch(team,8)
bunch(team,8)
