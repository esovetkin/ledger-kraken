#!/bin/env python3

from math import isclose
import json
import krakenex
import logging
import re
import sqlite3
import sys
import time
import numpy as np

from sklearn.cluster import KMeans

import ipdb

def query_tradable_pairs(kraken):
    res = kraken.query_public('AssetPairs')

    if len(res['error']):
        raise RuntimeError("API error:" + res['error'])

    return res['result']

def get_pairs_names(pairs, ignore_dotd = True):
    """
    :pairs: whatever query_tradable_pairs returns
    :ignore_dotd: ignore pairs that end with '.d'
    """
    res = list(pairs.keys())

    if ignore_dotd:
        r = re.compile('^.*\.d$')
        res = [x for x in res if not r.match(x)]

    return res

def query_ticker(kraken, pairs):
    """Query ticker information

    :kraken: Kraken object
    :pairs: list of string, pair names

    """
    args = {'pair':",".join(pairs)}
    res=kraken.query_public('Ticker',args)

    if len(res['error']):
        raise RuntimeError("API error:" + res['error'])

    return res['result']

def query_orderbook(kraken, pairs):
    """Query order book information

    :kraken: Kraken object
    :pairs: list of string, pair names

    """
    res = {}
    for pair in pairs:
        args = {'pair':pair}
        x = kraken.query_public('Depth',args)

        if len(x['error']):
            print("API error:" + res['error'])
            continue

        res[pair] = x['result']

    return res

def pair_name(key, pairs):
    """
    'XBTZEUR' -> ('XBT->ZEUR','ZEUR->XBT')
    """
    p = (pairs[key]['base'],pairs[key]['quote'])
    q = (pairs[key]['quote'],pairs[key]['base'])

    p = '->'.join(p)
    q = '->'.join(q)

    return (p,q)

def pair_fees(key, pairs):
    fp = pairs[key]['fees'][0][1]
    fq = pairs[key]['fees_maker'][0][1]

    return (fp/100,fq/100)

def orderbook_entry2array(orderbook_entry,invert_volume=False):
    """Convert orderbook entry to np.array

    :orderbook_entry: list of tuples of 3
    :invert_volume: if True invert volume
    :return: 2d np.array
    """
    if not isinstance(orderbook_entry,np.float):
        orderbook_entry = np.array(orderbook_entry)
        orderbook_entry = orderbook_entry.astype(float)

    p = orderbook_entry[:,0]
    v = orderbook_entry[:,1]

    if invert_volume:
        p = 1/p
        v = v/p

    return np.array(list(zip(p,v)))

def dict_price_volume_interval(pair_key,cpcv):
    """
    :pair_key: name of the pair
    :cpcv: whatever orderbook_entry2array returns
    :return: dictionary '<pair_key>#<v1><-><v2>': float
    """
    p = cpcv[:,0]
    v = cpcv[:,1]
    v = np.cumsum(v)

    res = {}
    for i in range(v.shape[0]):
        vl = v[i-1] if i > 0 else 0
        vu = v[i]
        key = pair_key+'#'+str(vl)+'<->'+str(vu)
        res[key] = p[i]

    # assume the last order in orderbook is infinite
    vl = v[-1]
    vu = 'Inf'
    key = pair_key+'#'+str(vl)+'<->'+str(vu)
    res[key] = p[-1]

    return res

def price_matrix(ticker, pairs):
    """Compute price matrix including the fees

    :orderbook: whatever query_orderbook returns
    :pairs: whatever query_tradable_pairs returns

    """
    res = {}

    for key,item in ticker.items():
        p,q = pair_name(key,pairs)
        fp,fq = pair_fees(key,pairs)

        res[p] = float(item['a'][0])*(1-fp)
        res[q] = 1/float(item['b'][0])*(1+fq)

    return res

def depth_matrix(orderbook, pairs):
    """Compute matrix prices with available volumes

    :orderbook: whatever query_orderbook returns
    :pairs: whatever query_tradable_pairs returns
    :return: dict: 'str key'->float

    """
    res = {}

    for key,item in orderbook.items():
        p,q = pair_name(key,pairs)
        fp,fq = pair_fees(key,pairs)

        a = orderbook_entry2array(item[key]['asks'], False)
        b = orderbook_entry2array(item[key]['bids'], True)
        a[:,0] = a[:,0]*(1-fp)
        b[:,0] = b[:,0]*(1-fq)

        res.update(dict_price_volume_interval(p,a))
        res.update(dict_price_volume_interval(q,b))

    return res

def invert_volume(key):
    """Invert volume of the depth_matrix

    :key: valid key of the depth_matrix
    """
    r=re.compile('^(.*)->(.*)#(.*)<->(.*)$')

    if not r.match(key):
        return key

    c1 = r.sub(r'\1',key)
    c2 = r.sub(r'\2',key)
    v1 = str(1/float(r.sub(r'\3',key)))
    v2 = str(1/float(r.sub(r'\4',key)))
    return c2+'->'+c1+'#'+v2+'<->'+v1

def cluster_volumes(depth_matrix, number_clusters=100):
    """Compute common volumes in depth_matrix

    :depth_matrix: whatever depth_matrix returns
    :number_clusters: number of clusters to combine the order volumes

    """
    r=re.compile('^.*->.*#(.*)<->(.*)$')

    v = []
    v += [float(r.sub(r'\1',x)) for x in depth_matrix.keys()]
    v += [float(r.sub(r'\2',x)) for x in depth_matrix.keys()]
    v = np.unique(sorted(v))
    l = np.zeros(v.shape)

    kmeans = KMeans(n_clusters = 100).fit(v[v!=float('inf')].reshape(-1,1))

    l[v!=float('inf')] = kmeans.cluster_centers_[
        kmeans.predict(v[v!=float('inf')].reshape(-1,1))][:,0]
    l[v==float('inf')] = float('inf')

    return {v[i]:l[i] for i in range(len(v))}

def approximate_depth_matrix(depth_matrix):
    """Reduce depth_matrix by making volumes common

    :depth_matrix: whatever depth_matrix returns
    :return: the same format as in depth_matrix

    """
    r=re.compile('^([A-Za-z]*)->.*#(.*)<->(.*)$')
    curs=set([r.sub(r'\1',x) for x in depth_matrix.keys()])

    res = {}

    for cur in curs:
        r=re.compile('^(.*->'+cur+')#(.*)<->(.*)$')
        m = {invert_volume(x):depth_matrix[x]
             for x in depth_matrix.keys() if r.match(x)}
        r=re.compile('^('+cur+'->.*)#(.*)<->(.*)$')
        m.update({x:depth_matrix[x]
                  for x in depth_matrix.keys() if r.match(x)})
        common=cluster_volumes(m)

        x = {}
        for key,item in m.items():
            k = r.sub(r'\1',key)+'#'+\
                str(common[float(r.sub(r'\2',key))])+'<->'+\
                str(common[float(r.sub(r'\3',key))])
            if k not in x:
                x[k]=[]
            x[k]+=[item]

        for key,item in x.items():
            x[key]=np.mean(item)

        d = {}
        for key,item in x.items():
            if r.sub(r'\2',key) == r.sub(r'\3',key):
                d[r.sub(r'\3',key)] = item

        for key,item in x.items():
            if r.sub(r'\2',key) in d:
                x[key] = (item + d[r.sub(r'\2',key)])/2

        x = {key:item for key,item in x.items()
             if r.sub(r'\2',key) != r.sub(r'\3',key)}

        res.update(x)

    return res

def save_json(fn,data):
    with open(fn,'w') as f:
        json.dump(data,f)

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
    latest_entry_time = arg['end']

    while (True):

        try:
            # try to make query with kraken
            t = kraken.query_private(query,arg)

            # raise exception in case of some error
            if (len(t['error'])):
                raise Exception("API error occured",t['error'])

        except Exception as e:
            logging.error("Error while quering ",query,": ",e)
            # sleep
            time.sleep(timeout)
            continue

        # count number of items. Break the loop if no more entries
        # left
        if (len(t['result'][keyname]) == 0):
            break

        # obtain the time of the latest oldest
        arg['end'] = min([t['result'][keyname][key]['time']
                          for key in t['result'][keyname].keys()])

        # the condition will be satisfied if no new data is fetched
        if (isclose(arg['end'],latest_entry_time)):
            break
        else:
            latest_entry_time = arg['end']

        # update dictionary
        data.update(t['result'][keyname])

        # some debug info
        print("start: ", arg['start'])
        print("end: ", arg['end'])
        print("number of entries: ", len(t['result'][keyname]))

        # timeout for kraken api
        time.sleep(timeout)

    return data

def search_fields(data,name,what=str,try_to_return=False):
    """Search nested lists and dicts

    :data: nested lists and dicts
    :name: name of the field
    :what: type of the data to return
    :try_to_return: if True try to exist recursion
    :return: list of 'what' variables
    """
    if try_to_return and isinstance(data,what):
        return [data]

    res = []
    if isinstance(data,list):
        for x in data:
            res += search_fields(data=x,
                                 name=name,what=what,
                                 try_to_return=False)

    if isinstance(data,dict):
        for key,item in data.items():
            res += search_fields(data=item,
                                 name=name,what=what,
                                 try_to_return=(key == name))

    return res

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


def _rou(value, currency):
    """
    Round up for printing ledger, such that it will fit to double entry

    value -- the volume of currency
    currency -- the corresponding currency
    """
    prec_list = {'XBT' : 3,
                 'EUR' : 3,
                 'XRP' : 3,
                 'XLM' : 8
                 }

    fmt = "{:.%if}"%prec_list[currency] if currency in prec_list else "{:.9f}"

    return fmt.format(value)




def trade2ledger(entry, account_fee, account):
    """Convert a list of entries to a ledger format

    entry --- list of length 2
    result --- string in ledger format
    """
    # currency
    curr0 = entry[0]['asset'][1:]
    curr1 = entry[1]['asset'][1:]

    # cost including fees
    cost0 = _rou(float(entry[0]['amount']) - float(entry[0]['fee']),curr0)
    cost1 = _rou(float(entry[1]['amount']) - float(entry[1]['fee']),curr1)

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

    res+=fmt_fee.format(account_fee,_rou(float(entry[0]['fee']),curr0),curr0)
    res+=fmt_fee.format(account_fee,_rou(float(entry[1]['fee']),curr1),curr1)

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

    # currency
    curr = entry[0]['asset'][1:]

    # cost including fees
    cost = _rou(float(entry[0]['amount']) - float(entry[0]['fee']),curr)

    # date
    date = time2date(entry[0]['time'])

    # trade_id
    id = entry[0]['refid']

    #pretty printing
    indent=' '*4
    fmt=indent+'{:<26}{:>22} {:3}\n'

    res ='{} {}\n'.format(date,id)
    res+=fmt.format(account_fee,_rou(float(entry[0]['fee']),curr),curr)
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

    logging.info("Wrote " + str(len(ledger)) + " entries.")

    save_timestamp(data, ftimestamp)
    logging.info("Saved timestamp")


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
        logging.error(exc)
        raise


    try:
        # make a query to kraken
        t = kraken.query_private('AddOrder',arg)
        print(t)
    except Exception as exc:
        logging.error(exc)
        raise
    except:
        logging.error("No connection")
        raise

    if (len(t['error'])):
        logging.error("API error occured",t['error'])
        raise Exception("API error")


def depth_format(result,pair):
    """
    Display the table of depth

    result -- result of public query of depth : depth['result']
    pair -- currency pair

    """
    wc = 16 #width of each column

    table = "Order Book {}/{}\n\n".format(pair[1:4],pair[5:])

    fmttitle='{:^%i}  {:^%i}\n'%(3*wc+5,3*wc+5)
    table+=fmttitle.format('Buying','Selling')

    #table entries formatting
    fmtt='{0:1}{5:^%i}{0:1}{1:^%i}{0:1}{2:^%i}{0:1}  {0:1}{3:^%i}{0:1}{4:^%i}{0:1}{6:^%i}{0:1}\n'%(wc+4,wc,wc,wc,wc,wc+4)
    hline=fmtt.format('+','-'*wc,'-'*wc,'-'*wc,'-'*wc,'-'*(wc+4),'-'*(wc+4))

    table += hline
    table += fmtt.format('|','Volume','Price','Price','Volume','Cum. Vol','Cum. Vol')
    table += hline

    curr1 = pair[1:4]
    c_ask,c_bid = 0,0 #cumulative values
    for bid,ask in zip(result[pair]['bids'],result[pair]['asks']):
        c_bid += float(bid[1])
        c_ask += float(ask[1])
        table += fmtt.format('|',bid[1],bid[0],ask[0],ask[1],_rou(c_bid,curr1),_rou(c_ask,curr1))

    table+=hline

    return table

