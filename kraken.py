#!/bin/env python3

import krakenex

import time

from math import ceil

class Kraken(krakenex.API):
    """A wrap for the krakekex with API call rate control

    """
    
    def __init__(self, key = '', secret = '', conn = None, tier = 3):
        # call constructor of the parent
        krakenex.API.__init__(self, key = key, secret = secret, conn = conn)

        # set counter and timestamp
        self._counter = 0
        self._counter_time = time.time()

        if (tier not in [2,3,4]):
            raise Exception("Wrong tier number")
        
        self._tier = tier

    def _query_cost(self, urlpath):
        """Determines cost of the urlpath query

        urlpath --- path specified in _query

        return integer
        """

        # determine cost depending on the query
        if "private/Ledgers" in urlpath or "private/QueryLedgers" in urlpath or\
           "private/Trades" in urlpath or "private/QueryTrades" in urlpath:
            return 2
        elif "private/AddOrder" in urlpath or "private/CancelOrder" in urlpath:
            return 0
        else:
            return 1
        

    def _if_blocked(self):
        """Determines whether call rate limit is too high
        
        return True or False
        """

        # determine new counter: tier 2 users reduce count every 3
        # seconds, tier 3 users reduce count every 2 seconds, tier 4
        # users reduce count every 1 second.
        self._counter -= (time.time() - self._counter_time)/(4-(self._tier-1))

        # check if the counter is negative
        if (self._counter < 0):
            self._counter = 0
            
        self._counter_time = time.time()

        # determine if blocked
        if 2 == self._tier:
            return ceil(self._counter) >= 15
        elif 3 == self._tier or 4 == self._tier:
            return ceil(self._counter) >= 20
        
    def _query(self, urlpath, req = {}, conn = None, headers = {}):
        """Redefinition of low-level query handling

        """
        
        # determine cost of the query and add up to the counter
        self._counter += self._query_cost(urlpath)
        
        while (self._if_blocked()):
            print("blocked, counter = ",self._counter)
            time.sleep(1)
            
            
        # call the parent function
        return super(Kraken, self)._query(urlpath = urlpath, req = req, \
                                          conn = conn, headers = headers)

