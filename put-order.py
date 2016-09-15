#!/bin/env python


# filename keys
filename_keys = "keys/albus-test.key"

import krakenex

import sys

from functions import order_str

if __name__ == '__main__':
        
    # init krakenex API
    kraken = krakenex.API()
    kraken.load_key(filename_keys)

    order_str(kraken, ' '.join(sys.argv[1:]))
    
