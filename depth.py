#!/bin/env python3

import krakenex

import sys

from tabulate import tabulate

k = krakenex.API()

# load keys
k.load_key('keys/albus-test.key')



arg = dict()

arg['pair'] = sys.argv[1]
arg['count'] = '30'

depth = k.query_public('Depth',arg)


try:
    print(tabulate(depth['result']['XXRPXXBT'], tablefmt='orgtbl'))
except:
    print(depth['error'])
