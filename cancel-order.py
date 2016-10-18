#!/bin/env python3

from kraken import Kraken

import sys

k = Kraken()

# load keys
k.load_key('keys/albus.key')

arg = {'txid': ' '.join(sys.argv[1:])}

t = k.query_private('CancelOrder',arg)

print(t)
