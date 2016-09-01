#!/bin/env python3

# install: https://github.com/veox/python3-krakenex
import krakenex

# for storing downloaded data
import json

# for time and sleep
import time


def query_all_entries(kraken, query, keyname, start, end, timeout=5):
    """Query all entries present in kraken database

    Kraken allows only to get limited amount of data at a
    time. Therefore, we split this on several steps. See notes above
    about 'call counter'

    Note, this function is supposed to be used only once in a life.
    
    kraken --- krakenex API
    query  --- query name of the API
    keyname --- keyname in the resulting dictionary
    start --- earliest time point (in seconds from epoch)
    end --- latest time point (in seconds from epoch)
    timeout --- timeout in seconds before queries

    return --- dictionary
    """
    
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


def time2date(t):
    """
    Convert time to ledger date format
    
    time   --- time in seconds since epoch
    return --- string of date in ledger format
    """
    return time.strftime('%Y/%m/%d', time.localtime(t))


def reformat(trades):
    """
    Reformat raw data from query to human readable format. 

    trades --- dict with trades/ledger data

    return --- list with trades/ledger entries
    """

    res=list()
    for tid,trade in trades.items():
        trade['id'] = tid
        res.append(trade)

    return res


def splitpair(pair):
    """
    Splits pair of currencies

    pair --- pair of currencies, e.g. XXRPXXBT

    return list of length 2
    """
    res = list()

    res.append(pair[1:4])
    res.append(pair[5:])
    return res


def print_trade(entry):
    """Print entries in ledger format

    ledger --- reformated ledger
    trades --- reformated trades

    return --- dict:
         trade_id - ledger string

    """
    pair = splitpair(entry['pair'])

    indent='\n    '
    account_fee = "Expenses:Taxes:Kraken"
    account = "Assets:Kraken"
    
    res=time2date(entry['time']) + "  " +\
        entry['type'] + " " + pair[0] + "; " +\
        entry['id'] + indent

    res=res + account_fee + "  " +\
        entry["fee"] + " " + pair[1] + indent
    
    res=res + account  + "  " + \
        ("-" if entry['type'] == 'buy' else "") + \
        entry['cost'] + " " + pair[1] + indent

    res=res + account + "  " +\
        ("-" if entry['type'] == 'sell' else "") +\
        entry['vol'] + " " + pair[0] + indent

    return res
    
    

if __name__ == '__main__':
    """
    Describe what it does 
    """

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
    # kraken = krakenex.API()
    # kraken.load_key("keys/albus-test.key")

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

    # # get ledger history
    # ledger = query_all_entries(kraken,'Ledgers','ledger',1451602800,1472643007,5)
    # # save in json data
    # with open('data/ledger.json','w') as fp:
    #    json.dump(ledger, fp, indent = 2)

    # # get trades history
    # trades = query_all_entries(kraken,'TradesHistory','trades',1451602800,1472643007,5)
    # # save in json data
    # with open('data/trades.json','w') as fp:
    #     json.dump(trades, fp, indent = 2)

    
    # load the raw data
    with open('data/trades.json', 'r') as fp:
        trades = json.load(fp)

    # reformat trades and sort
    tradesh = sorted(reformat(trades), key=(lambda x: x['time']))
    
    # write to file
    with open('data/trades_h.json','w') as fp:
        json.dump(tradesh, fp, indent = 2)


    # read ledger data
    with open('data/ledger.json', 'r') as fp:
        ledger = json.load(fp)

    # reformat ledger
    ledgerh = sorted(reformat(ledger),key=(lambda x: x['time']))
    
    with open('data/ledger_h.json', 'w') as fp:
        json.dump(ledgerh, fp, indent = 2)

    
