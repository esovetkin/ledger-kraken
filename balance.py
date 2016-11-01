#!/bin/env python3

from kraken import Kraken

import sys


# init krakenex API
k = Kraken()

# load keys
k.load_key('keys/albus-test.key')

bal = k.query_private('Balance')['result']

for key,value in sorted(bal.items()):
    print(key + ": " + str(value))
