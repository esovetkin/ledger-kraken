#!/bin/env python3

# install: https://github.com/veox/python3-krakenex
import krakenex

# for storing downloaded data
import json

# for time and sleep
import time

import sys

import sqlite3

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

            # raise exception in case of some error
            if (len(t['error'])):
                raise Exception("API error occured",t['error'])

        except Exception as e:
            print("Error while quering ",query,": ",e)
            # sleep
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


def trade2ledger(entry, account_fee, account):
    """Convert a list of entries to a ledger format

    entry --- list of length 2
    result --- string in ledger format
    """    
    # currency
    curr0 = entry[0]['asset'][1:]
    curr1 = entry[1]['asset'][1:]

    # round only up to 3 significant digit if EUR 
    rou = lambda p,c : "{:.3f}".format(p) if c=='EUR' else "{:.9f}".format(p)

    # cost including fees
    cost0 = rou(float(entry[0]['amount']) - float(entry[0]['fee']),curr0)    
    cost1 = rou(float(entry[1]['amount']) - float(entry[1]['fee']),curr1)
    
    price0 = "{:<7} {} {}".format(("BUY AT" if float(entry[0]['amount']) > 0 else "SELL AT" ),
                                      abs(float(entry[0]['amount'])/float(entry[1]['amount'])),
                                      entry[0]['asset'] + entry[1]['asset']) 
    price1 = "{:<7} {} {}".format(("BUY AT" if float(entry[1]['amount']) > 0 else "SELL AT" ),
                                      abs(float(entry[1]['amount'])/float(entry[0]['amount'])),
                                      entry[1]['asset'] + entry[0]['asset']) 
    

    
    
    # date
    date = time2date(entry[0]['time'])

    # trade_id
    id = entry[0]['refid']

    #pretty printing
    indent=' '*4
    fmt_fee = indent+'{:<26}{:>22} {:3}\n'
    fmt=indent+'{:<26}{:>22} {:3} ; {}\n'
    
    res ='{} Trade id: {}\n'.format(date,id)

    res+=fmt_fee.format(account_fee,rou(float(entry[0]['fee']),curr0),curr0)
    res+=fmt_fee.format(account_fee,rou(float(entry[1]['fee']),curr1),curr1)

    res+=fmt.format(account,cost0,curr0, price0)
    res+=fmt.format(account,cost1,curr1, price1)

    return res


def deposit2ledger(entry, account_fee, account):
    """Convert deposit/withdrawal/transfer to a ledger format
    
    entry --- list of length 1
    result --- string in ledger format
    """
    # sub-account for withdrawals/transfer/funding
    account2 = account + ":" + entry[0]['type']

    # round only up to 3 significant digit if EUR 
    rou = lambda p,c : "{:.3f}".format(p) if c=='EUR' else "{:.9f}".format(p)

    # currency
    curr = entry[0]['asset'][1:]

    # cost including fees
    cost = rou(float(entry[0]['amount']) - float(entry[0]['fee']),curr)

    # date
    date = time2date(entry[0]['time'])

    # trade_id
    id = entry[0]['refid']

    #pretty printing
    indent=' '*4
    fmt=indent+'{:<26}{:>22} {:3}\n'
    
    res ='{} {}\n'.format(date,id)
    res+=fmt.format(account_fee,rou(float(entry[0]['fee']),curr),curr)
    res+=fmt.format(account,cost,curr)
    res+=fmt.format(account2,'','')

    return res
    

def convert2ledger(ledger, account_fee, account):
    """Converts ledger entries to a double entry in the format of ledger

    ledger --- ledger list
    account_fee --- name for the fee account in ledger
    account --- name for the kraken account in ledger

    return --- list of character in ledger format 
    """
    # get unique trade ids
    ids = list(set([x['refid'] for x in ledger]))

    # resulting list of strings. each entry is one entry in ledger
    res = list('\n')
        
    for id in ids:
        # get list of trades corresponding to the id
        entry = [x for x in ledger if x['refid'] == id]

        # case of trade
        if len(entry) == 2:
            if (entry[0]['type'] != 'trade') | (entry[1]['type'] != 'trade'):
                print("ledger entries are not trade")
                sys.exit()
            
            res.append(trade2ledger(entry, account_fee, account))

        # case of withdrawal/transfer/funding
        if len(entry) == 1:
            if (entry[0]['type'] == 'trade'):
                print("lonely trade")
                continue
                
            res.append(deposit2ledger(entry, account_fee, account))

        # in case some error in ledger
        if len(entry) < 1 or len(entry) > 2:
            print(entry)
            print("length = ",len(entry))
            print("unknown transaction")
            sys.exit()

    return res    


def save_timestamp(ledger, filename):
    """Save the time of the latest trade in file
    
    ledger --- downloaded ledger data
    filename --- filename of the timestamp
    return --- nothing
    """
    time = max([x['time'] for key,x in ledger.items()])

    with open(filename,'w') as fp:
        fp.write(str(time))


def read_timestamp(filename):
    """Read the time of the latest trade from file

    filename --- filename of the timestamp
    return --- float, should be time in seconds from epoch
    """
    try:
        with open(filename,'r') as fp:
            return float(fp.read())
    except:
        return 1

        
def sync(kraken, ftimestamp, fledger, timeout, account_fee, account):
    """Synchronise ledger data
    
    ftimestamp --- filename where the timestamp is
    fledger --- filename of the ledger file
    timeout --- timeout between transactions

    """
    # get the period of time
    start = read_timestamp(ftimestamp)
    end = time.time()

    # query new entries
    data = query_all_entries(kraken,'Ledgers','ledger',start,end,timeout)
    
    # convert to ledger format
    ledger = convert2ledger(reformat(data, entry_type="ledger"), account_fee, account)

    with open(fledger, 'a+') as fp:
        fp.write("\n".join(sorted(ledger)))

    print("Wrote " + str(len(ledger)) + " entries.")

    save_timestamp(data, ftimestamp)
    print("Saved timestamp")


def str2krakenOrder(string):
    """Converts string with order to dictionary
    
    In case it fails to convert an exception is called

    """
    string = string.split()
    
    res = {'ordertype': 'limit'}

    # # debug
    # res['validate'] = 1
    
    if (len(string) != 6):
        raise Exception("String contains incorrect number of words!")

    # check the first word
    if (string[0] != 'buy' and string[0] != 'sell'):
        raise Exception("Wrong order string!")
    
    res['type'] = string[0]

    # set volume
    res['volume'] = string[1]

    # set price
    res['price'] = string[4]
    
    # deal with currency pairs
    first = string[2]
    second = string[5]

    # TODO should be a parameter
    valid_currencies = ['EUR','USD','ETH','ETC','XBT','DAO','LTC','XDG','XLM','XRP']
    
    # check if this are good names
    if (first not in valid_currencies) or (second not in valid_currencies):
        raise Exception("Invalid currencies")

    res['pair'] = first + second
    
    return res
    
    
def order_str(kraken, string):
    """Put a limit order to buy/sell

    Convert a given string into kraken API language and tries to set
    the order. Print given from kraken feedback.

    string --- string like 'buy 0.5 BTC @ 534 EUR'

    """

    arg = {}
    
    try:
        arg = str2krakenOrder(string)
    except Exception as exc:
        print(exc)
        raise
        

    try:
        # make a query to kraken
        t = kraken.query_private('AddOrder',arg)
        print(t)
    except Exception as exc:
        print(exc)
        raise
    except:
        print("No connection")
        raise

    if (len(t['error'])):
        print("API error occured",t['error'])
        raise Exception("API error")


