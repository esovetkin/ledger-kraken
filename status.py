#!/bin/python

from functions import query_all_entries, search_fields
from kraken import Kraken
import json
import time

def read_json(fn):
    with open(fn,'r') as f:
        return json.load(f)

def write_json(data,fn):
    with open(fn,'w') as f:
        json.dump(data,f)

def get_latest_timestamp(fn):
    try:
        data=read_json(fn)
    except:
        return 0

    return max(search_fields(data,'time',what=float))

def sync(kraken, fn):
    start = get_latest_timestamp(fn)
    end = time.time()

    try:
        data=read_json(fn)
    except:
        data = {}

    data.update(query_all_entries(kraken,
                                  'Ledgers','ledger',
                                  start, end))

    with open(fn,'w') as f:
        json.dump(data,f)

    return 0

def bal(fn):
    data=read_json(fn)

    bal = {}

    for key, item in data.items():
        if item['asset'] not in bal:
            bal[item['asset']] = 0

        bal[item['asset']] += float(item['amount']) - float(item['fee'])

    return bal

def trades(fn):
    data=read_json(fn)

    trades = {}

    for key, item in data.items():
        if item['refid'] not in trades:
            trades[item['refid']] = []

        item['amount'] = float(item['amount']) - float(item['fee'])
        trades[item['refid']] += [item]

    return trades

def remove_negative(data):
    X = sorted(data, key=lambda x: x['time'])

    negative = (i for i in range(len(X)) if X[i]['volume'] < 0)
    positive = (i for i in range(len(X)) if X[i]['volume'] >= 0)
    flag_delete = []

    flag = True
    try:
        n = next(negative)
        p = next(positive)
    except StopIteration:
        flag = False

    while flag:
        try:
            if X[p]['volume'] > abs(X[n]['volume']):
                X[p]['volume'] += X[n]['volume']
                X[n]['volume'] = 0
                flag_delete += [n]
                n = next(negative)
            else:
                X[n]['volume'] += X[p]['volume']
                X[p]['volume'] = 0
                flag_delete += [p]
                p = next(positive)
        except StopIteration:
            flag = False

    X = [X[i] for i in range(len(X)) if i not in flag_delete]

    return X

def trades_pairs(fn):
    t={key:item for key,item in trades(fn).items() if len(item) == 2}

    res = {}
    for key,item in t.items():
        item = sorted(item,key=lambda x: x['asset'])
        pair = (item[0]['asset'],item[1]['asset'])
        if pair not in res:
            res[pair] = []

        res[pair] += [{'volume':item[0]['amount'],
                             'price':abs(item[1]['amount']/item[0]['amount']),
                             'time':max(item[0]['time'],item[1]['time'])}]

    return res

def transfers(fn):
    t={key:item for key,item in trades(fn).items() if len(item) == 1}

    res = {}
    for key,item in t.items():
        x = item[0]
        if x['asset'] not in res:
            res[x['asset']] = []

        res[x['asset']] += [x]

    return res

def portfolio(fn):
    res = trades_pairs(fn)
    for key, item in res.items():
        res[key] = remove_negative(item)
    return res

# kraken = Kraken()
# kraken.load_key('keys/albus.key')
# fn = 'data/kraken_Ledgers.json'

#sync(kraken, fn)
