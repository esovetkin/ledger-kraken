#!/bin/env python3

import numpy as np
from sklearn import svm
from sklearn.model_selection import KFold, cross_val_score
import json

def get_classes(data, T, rho):
    """Get classes for classification from the market price changes. Class
    1 if price has increased at least linearly with rate rho until
    time point T (that corresponds to T*time interval data). Class -1
    if price decreased analogously. Class 0 if price doesn't belong to
    class 1 or -1.

    data --- orderBook data

    T --- time period for price rise/decrease

    rho --- rate of increase/decrease to make classes

    """
    price = [x[1] for x in data]
    
    # calculate price change in percentage
    diff=[]
    for i in range(1,T):
        diff+=[(np.array(price[i:])/np.array(price[:-i])-1)[:-(T-i)]]

    # get index of times when price rose more than .0042 after t*3 minutes
    i_pos = ~np.zeros(len(diff[0]),dtype=bool)
    for x in range(0,T):
        i_pos = i_pos & (diff[x-1] > rho*x)

    i_neg = ~np.zeros(len(diff[0]),dtype=bool)
    for x in range(0,T):
        i_neg = i_neg & (diff[x-1] < -rho*x)

    res=np.zeros(len(data) - T,dtype=np.int)
    res[i_pos] = 1
    res[i_neg] = -1

    return res

def get_features(data, T=1, standardise=True):
    """Combine orders in a table combining several time points together

    data --- orderBook data

    T --- number of prior time points to combine

    standardise --- 
    """
    orders= [x[0] for x in data]

    #orders = [list(np.array(x)/max(x)) for x in orders]

    return orders

with open("./orderBook.json") as x:
    data = json.load(x)

Y = get_classes(data,5,0.0042/2)
X = get_features(data)

X = X[40000:len(Y)]
Y = Y[40000:len(Y)]

print(X[1:10])
print(Y[1:10])

#weights = {1: sum(Y == 1)/len(Y), -1: sum(Y == -1)/len(Y), 0: sum(Y == 0)/len(Y)}
weights = {1: len(Y)/sum(Y == 1), -1: len(Y)/sum(Y == -1), 0: len(Y)/sum(Y == 0)}

print(weights)

print("Positive: " + str(sum(Y == 1)))
print("Negative: " + str(sum(Y == -1)))
print("Zero: " + str(sum(Y == 0)))

svc = svm.SVC(C=1.0,cache_size=5000,kernel='rbf', gamma='auto',
              class_weight = weights)

print("do cv...")

k_fold = KFold(n_splits=3)

score = cross_val_score(svc, X, Y, cv=k_fold, n_jobs=-1)
    
print(score)
