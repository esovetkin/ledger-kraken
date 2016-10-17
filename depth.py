#!/bin/env python3

import krakenex

import sys

from functions import depth_format

k = krakenex.API()



arg = dict()

arg['pair'] = sys.argv[1] if len(sys.argv) > 1 else 'XXBTZEUR' 
arg['count'] = '30'

depth = k.query_public('Depth',arg)

try:
    print(depth_format(depth['result'],arg['pair']))
except:
    print(depth['error'])
