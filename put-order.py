#!/bin/env python


# filename keys
filename_keys = "keys/albus.key"

from functions import depth_format

import sys

from functions import order_str

if __name__ == '__main__':
        
    # init krakenex API
    kraken = Kraken()
    kraken.load_key(filename_keys)

    order_str(kraken, ' '.join(sys.argv[1:]))
    
