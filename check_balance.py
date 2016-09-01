#!/bin/env python3

import krakenex

import sys

import json

import time

# init krakenex API
k = krakenex.API()

# load keys
k.load_key('keys/albus-test.key')

while (True):
    try:
        new_bal = k.query_private('Balance')['result']
    except:
        print("Cannot get balance")
        sys.exit()
        
    try:
        with open('data/balance.json', 'r') as fp:
            old_bal = json.load(fp)
    except:
        print("First run, a balance file will be created")
        old_bal = dict()
    
    if (old_bal != new_bal):
        print("Balance has changed")
            
        for key,value in sorted(new_bal.items()):
            print(key + ": " + str(value))

    with open('data/balance.json','w') as fp:
        json.dump(new_bal, fp, indent = 2)

    time.sleep(30)
    
