#!/bin/env python3

import krakenex

import sys

from tabulate import tabulate

k = krakenex.API()

# load keys
k.load_key('keys/albus-test.key')



orders = k.query_private('OpenOrders')

orders = orders['result']['open']

t = [{'pair':orders[key]['descr']['pair'],\
      'type':orders[key]['descr']['type'],\
      'price':orders[key]['descr']['price'],\
      'vol':orders[key]['vol'],\
      'key':key,\
      'status':orders[key]['status']} for key in orders.keys()]


print(tabulate(t, floatfmt="7.9f"))
