#!/bin/env python3

import krakenex


k = krakenex.API()

# load keys
k.load_key('keys/albus.key')

arg = {'txid': ' '.join(sys.argv[1:])}

k.query_private('CancelOrder',arg)
