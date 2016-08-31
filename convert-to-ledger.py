#!/bin/env python3

# install: https://github.com/veox/python3-krakenex
import krakenex

# for reading arguments
import sys

# for storing downloaded data
import json

# for time and sleep
import time

# types of query_private:
# * Balance 
# * TradeBalance
# * OpenOrders
# * ClosedBalance
# * QueryOrders
# * TradesHistory
# * QueryTrades
# * OpenPositions
# * Ledgers
# * QueryLedgers


# init krakenex API
kraken = krakenex.API()
kraken.load_key("keys/albus-test.key")

# query orders
#t = k.query_private("OpenOrders")

# set tier, for proper timeouts before calls:
# Every user of our API has a "call counter" which starts at 0.

# Ledger/trade history calls increase the counter by 2.

# Place/cancel order calls do not affect the counter.

# All other API calls increase the counter by 1.

# Tier 2 users have a maximum of 15 and their count gets reduced by 1
# every 3 seconds. Tier 3 and 4 users have a maximum of 20; the count
# is reduced by 1 every 2 seconds for tier 3 users, and is reduced by
# 1 every 1 second for tier 4 users.
#tier=3

# connection handler. \todo set timeout variable properly (depending on tier)
#conn = kraken.Connection("api.kraken.com",timeout=5)

# function to query all ledger entries make 5 seconds pause before
# each transaction. Function should be called only once in a life
def query_all_entries(kraken, query, keyname, start, end, timeout=5):
    
    # dictionary with extra parameters to the query
    arg=dict()
    arg['start'] = start
    arg['end'] = end

    data = dict()
    
    while (arg['start'] < arg['end']):

        try:
            t = kraken.query_private(query,arg)
        except:
            time.sleep(timeout)
            continue
        
        # raise exception in case of some error
        if (len(t['error'])):
            print("error occured")
            print(t['error'])
            time.sleep(timeout)
            continue
    
        # count number of items. Break the loop if no more entries
        # left
        if (len(t['result'][keyname]) == 0):
            break
        
        # return vector of times
        time_vector = [t['result'][keyname][key]['time']
                       for key in t['result'][keyname].keys()]
        
        arg['end'] = min(time_vector)-0.5

        # some debug info
        print("start: ", arg['start'])
        print("end: ", arg['end'])
        print("number of entries: ", len(t['result'][keyname]))        
        
        data.update(t['result'][keyname])

        # timeout for kraken api
        time.sleep(timeout)

    return data

# # get ledger history
# ledger = query_all_entries(kraken,'Ledgers','ledger',1451602800,1472643007,5)
# # save in json data
# with open('data/ledger.json','w') as fp:
#    json.dump(ledger, fp)

# # get trades history
# trades = query_all_entries(kraken,'TradesHistory','trades',1451602800,1472643007,5)
# # save in json data
# with open('data/trades.json','w') as fp:
#     json.dump(trades, fp)


# read json code    
with open('data/ledger.json', 'r') as fp:
    data = json.load(fp)
