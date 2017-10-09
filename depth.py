#!/bin/env python3

import sys

from kraken import Kraken

from functions import depth_format

k = Kraken()

arg = dict()

arg['pair'] = sys.argv[1] if len(sys.argv) > 1 else 'XXBTZEUR' 
arg['count'] = '2000'

depth = k.query_public('Depth',arg)

try:
    print(depth_format(depth['result'],arg['pair']))
except:
    print(depth['error'])

import matplotlib.pyplot as plt
import numpy as np

v = list(np.cumsum([float(x[1]) for x in depth['result']['XXBTZEUR']['bids']]))[::-1] + list(np.cumsum([float(x[1]) for x in depth['result']['XXBTZEUR']['asks']]))
p = list([float(x[0]) for x in depth['result']['XXBTZEUR']['bids']])[::-1] + list([float(x[0]) for x in depth['result']['XXBTZEUR']['asks']])

plt.plot(p,v)
plt.show()
