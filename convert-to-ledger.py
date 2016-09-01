#!/bin/env python3

# install: https://github.com/veox/python3-krakenex
import krakenex

# for storing downloaded data
import json

# for time and sleep
import time

import sys

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

    last_end = 0
    
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

        # in case no new data is fetched
        if (arg['end'] == last_end):
            break
        else:
            last_end = arg['end']
        
        # return vector of times
        time_vector = [t['result'][keyname][key]['time']
                       for key in t['result'][keyname].keys()]
        
        arg['end'] = min(time_vector)

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
    entry_type --- is it trade or ledger

    return --- string of date in ledger format
    """
    return time.strftime('%Y/%m/%d', time.localtime(t))


def reformat(trades, entry_type):
    """
    Reformat raw data from query to human readable format. 

    trades --- dict with trades/ledger data

    return --- list with trades/ledger entries
    """

    res=list()
    for tid,trade in trades.items():
        trade['id'] = tid
        trade['entry_type'] = entry_type
        res.append(trade)

    return res


def trade2ledger(entry):
    """Convert a list of entries to a ledger format

    entry --- list of length 2
    result --- string in ledger format
    """
    # account names
    account_fee = "Expenses:Taxes:Kraken"
    account = "Assets:Kraken"
    
    # cost including fees
    cost0 = "{:.9f}".format(float(entry[0]['amount']) - float(entry[0]['fee']))    
    cost1 = "{:.9f}".format(float(entry[1]['amount']) - float(entry[1]['fee']))

    # currency
    curr0 = entry[0]['asset'][1:]
    curr1 = entry[1]['asset'][1:]
    
    # date
    date = time2date(entry[0]['time'])

    # trade_id
    id = entry[0]['refid']

    #pretty printing
    indent=' '*4
    fmt=indent+'{:<26}{:>30} {:3}\n'
    
    res ='{} {}\n'.format(date,id)
    res+=fmt.format(account_fee,entry[0]['fee'],curr0)
    res+=fmt.format(account_fee,entry[1]['fee'],curr1)

    res+=fmt.format(account,cost0,curr0)
    res+=fmt.format(account,cost1,curr1)

    return res

def deposit2ledger(entry):
    """Convert deposit/withdrawal/transfer to a ledger format
    
    entry --- list of length 1
    result --- string in ledger format
    """
    account_fee = "Expenses:Taxes:Kraken"
    account = "Assets:Kraken"
    account2 = account + ":" + entry[0]['type']

    # cost including fees
    cost = "{:.9f}".format(float(entry[0]['amount']) - float(entry[0]['fee']))

    # currency
    curr = entry[0]['asset'][1:]

    # date
    date = time2date(entry[0]['time'])

    # trade_id
    id = entry[0]['refid']

    #pretty printing
    indent=' '*4
    fmt=indent+'{:<26}{:>30} {:3}\n'
    
    res ='{} {}\n'.format(date,id)
    res+=fmt.format(account_fee,entry[0]['fee'],curr)
    res+=fmt.format(account,cost,curr)
    res+=fmt.format(account2,'','')

    return res
    

def convert2ledger(ids, ledger):
    """Converts ledger entries to a double entry in the format of ledger

    ids --- trade ids
    ledger --- ledger list

    return --- list of character in ledger format 
    """
    
    # get unique ids
    ids = list(set(ids))
    
    res = list()
        
    for id in ids:
        # get list of trades corresponding to the id
        entry = [x for x in ledger if x['refid'] == id]

        # case of trade
        if len(entry) == 2:
            if (entry[0]['type'] != 'trade') | (entry[1]['type'] != 'trade'):
                print("ledger entries are not trade")
                sys.exit()
            
            res.append(trade2ledger(entry))

        if len(entry) == 1:
            if (entry[0]['type'] == 'trade'):
                print("lonely trade")
                sys.exit()

            res.append(deposit2ledger(entry))

        if len(entry) < 1 or len(entry) > 2:
            print(entry)
            print("length = ",len(entry))
            print("unknown transaction")
            sys.exit()
            

    return res    
    

if __name__ == '__main__':
    """
    Describe what it does 
    """

    # init krakenex API
    kraken = krakenex.API()
    kraken.load_key("keys/albus-test.key")

    # connection handler. \todo set timeout variable properly (depending on tier)
    #conn = kraken.Connection("api.kraken.com",timeout=5)

    # # get ledger history
    # ledger = query_all_entries(kraken,'Ledgers','ledger',1451602800,time.time(),5)
    # # save in json data
    # with open('data/ledger.json','w') as fp:
    #    json.dump(ledger, fp, indent = 2)

    # # get trades history
    # trades = query_all_entries(kraken,'TradesHistory','trades',1451602800,time.time(),5)
    # # save in json data
    # with open('data/trades.json','w') as fp:
    #     json.dump(trades, fp, indent = 2)

    
    # read ledger data
    with open('data/ledger.json', 'r') as fp:
        ledger = json.load(fp)

    ledger = reformat(ledger, entry_type="ledger")
        
    entries = convert2ledger([x['refid'] for x in ledger], ledger)
    
    
    # write ledger file    
    with open('data/ledger_kraken.log','w') as fp:
        fp.write("\n".join(sorted(entries)))

    
    
    
