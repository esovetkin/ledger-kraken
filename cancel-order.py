#!/bin/env python3

import krakenex

import sys

k = krakenex.API()

# load keys
k.load_key('keys/albus.key')

arg = {'txid': ' '.join(sys.argv[1:])}

t = k.query_private('CancelOrder',arg)

print(t)
