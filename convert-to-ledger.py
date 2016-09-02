#!/bin/env python3

# install: https://github.com/veox/python3-krakenex
import krakenex

# for storing downloaded data
import json

# for time and sleep
import time

import sys

# defining some global varible (to replace with configuration)

# account names
account_fee = "Expenses:Taxes:Kraken"
account = "Assets:Kraken"

# filename for the timestamp
filename_timestamp = "data/timestamp"

# ledger filename
filename_ledger = "data/ledger.log"

# filename keys
filename_keys = "keys/albus-test.key"

# timeout
timeout = 5

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
    arg={'start': start, 'end': end}

    # result data
    data = dict()

    # in this variable is stored the time of the latest
    latest_entry_time = 0
    
    while (True):

        try:
            # try to make query with kraken
            t = kraken.query_private(query,arg)
        except:
            # sleep
            time.sleep(timeout)
            continue

        # raise exception in case of some error
        if (len(t['error'])):
            print("API error occured",t['error'])
            time.sleep(timeout)
            continue
    
        # count number of items. Break the loop if no more entries
        # left
        if (len(t['result'][keyname]) == 0):
            break
        
        # the condition will be satisfied if no new data is fetched
        if (arg['end'] == latest_entry_time):
            break
        else:
            latest_entry_time = arg['end']
        
        # obtain the time of the latest oldest
        arg['end'] = min([t['result'][keyname][key]['time']
                          for key in t['result'][keyname].keys()])

        # update dictionary
        data.update(t['result'][keyname])

        # some debug info
        print("start: ", arg['start'])
        print("end: ", arg['end'])
        print("number of entries: ", len(t['result'][keyname]))        
        
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
    fmt=indent+'{:<26}{:>22} {:3}\n'
    
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
    # sub-account for withdrawals/transfer/funding
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
    fmt=indent+'{:<26}{:>22} {:3}\n'
    
    res ='{} {}\n'.format(date,id)
    res+=fmt.format(account_fee,entry[0]['fee'],curr)
    res+=fmt.format(account,cost,curr)
    res+=fmt.format(account2,'','')

    return res
    

def convert2ledger(ledger):
    """Converts ledger entries to a double entry in the format of ledger

    ids --- trade ids
    ledger --- ledger list

    return --- list of character in ledger format 
    """
    # get unique trade ids
    ids = list(set([x['refid'] for x in ledger]))

    # resulting list of strings. each entry is one entry in ledger
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

        # case of withdrawal/transfer/funding
        if len(entry) == 1:
            if (entry[0]['type'] == 'trade'):
                print("lonely trade")
                continue
                
            res.append(deposit2ledger(entry))

        # in case some error in ledger
        if len(entry) < 1 or len(entry) > 2:
            print(entry)
            print("length = ",len(entry))
            print("unknown transaction")
            sys.exit()

    return res    


def save_timestamp(ledger):
    """Save the time of the latest trade in file
    
    ledger --- downloaded ledger data
    return --- nothing
    """
    time = max([x['time'] for key,x in ledger.items()])

    with open(filename_timestamp,'w') as fp:
        fp.write(str(time))


def read_timestamp():
    """Read the time of the latest trade from file

    return --- float, should be time in seconds from epoch
    """
    try:
        with open(filename_timestamp,'r') as fp:
            return float(fp.read())
    except:
        return 1

        
def sync(kraken):
    """Synchronise ledger data
    """
    # get the period of time
    start = read_timestamp()
    end = time.time()

    # query new entries
    data = query_all_entries(kraken,'Ledgers','ledger',start,end,timeout)
    
    # convert to ledger format
    ledger = convert2ledger(reformat(data, entry_type="ledger"))

    with open(filename_ledger, 'a+') as fp:
        fp.write("\n".join(sorted(ledger)))

    print("Wrote " + str(len(ledger)) + " entries.")

    save_timestamp(data)
    print("Saved timestamp")
    
    
if __name__ == '__main__':
    """
    Describe what it does 
    """
    # init krakenex API
    kraken = krakenex.API()
    kraken.load_key(filename_keys)
    
    # connection handler. \todo set timeout variable properly (depending on tier)
    #conn = kraken.Connection("api.kraken.com",timeout=timeout)

    sync(kraken)
