#!/bin/python

from datetime import datetime
from functions import log_arbitrage

if __name__ == '__main__':
    path = os.path.join(
        'arbitrage',
        datetime.now().strftime('%Y%m%d-%H:%M'))

    log_arbitrage(path)



