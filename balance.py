#!/bin/env python3

import krakenex

import sys


# init krakenex API
k = krakenex.API()

# load keys
k.load_key('keys/albus-test.key')

bal = k.query_private('Balance')['result']

for key,value in sorted(bal.items()):
    print(key + ": " + str(value))
