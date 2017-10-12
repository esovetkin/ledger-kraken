#!/bin/env python3

from kraken import Kraken, KrakenData
import numpy as np
import json

kraken = KrakenData(db_path="data/data.db",key_path="keys/albus.key")

def get_time_points(observe_each = 180, max_gap = 1000):
    """Get available time points when order book was collected

    max_gap --- max gap in seconds to be allowed between
    observations. In case observations in some period are missing then
    we do not query orderBook at that point

    observe_each --- number of seconds between consecutive observation
    in the produced interval
    """

    c = kraken._dbconn.cursor()

    # query all time_l
    try:
        c.execute('SELECT DISTINCT time_l FROM orderBook ORDER BY time_l')
        time_l = c.fetchall()
    except Exception as e:
        logging.error("Error quering timestamps from orderBook",e)
        kraken._dbconn.rollback()
        raise e
    kraken._dbconn.commit()

    # convert list of tuples to list
    time_l = [x[0] for x in time_l]

    # get sequence of times
    res = list(range(min(time_l),max(time_l),observe_each))

    # calculate times of big gaps
    big_diff = filter(lambda x: x[2] > max_gap,
                      zip(range(1,len(time_l)), time_l,
                          np.array(time_l[1:]) - np.array(time_l[:-1])))

    # remove the gap times from the resulting observation points
    for i,t,d in big_diff:
        res = filter(lambda x: x <= time_l[i-1] or x >= time_l[i], res)
    res = list(res)

    return res

def process_orderbook(data, price_interval = 0.05, len_bids_asks = 20):
    """Process the query result and produce vectors of fixed lengths of
    asks and bids volumes around an interval of the market price, and
    the current market price

    data --- result of _select_from_OrderBook method

    price_interval --- percentage around the current market price to
    consider the orderBook

    len_bids_asks --- lengths of asks and bids output vectors

    """
    # get asks and bids from queried data
    asks = sorted(filter(lambda x: x[2] == "asks", data),key=lambda x: x[0])
    bids = sorted(filter(lambda x: x[2] == "bids", data),key=lambda x: -x[0])

    # get market price (average between largest bids and smallest asks)
    market_price=(max([float(x[0]) for x in bids]) + min([float(x[0]) for x in asks]))/2

    # calculate accumulated volume and corresponding price
    volume = list(np.cumsum([float(x[1]) for x in bids]))[::-1] + list(np.cumsum([float(x[1]) for x in asks]))
    price = list([float(x[0]) for x in bids])[::-1] + list([float(x[0]) for x in asks])

    res=[]
    # price points at which we evaluate volume
    for p in np.linspace((1-price_interval)*market_price,
                         (1+price_interval)*market_price,
                         len_bids_asks):
        # get index inside price vector
        try:
            i = list(filter(lambda i: price[i] <= p and price[i+1] > p,
                            range(1,len(price)-1)))[0]
        except IndexError as e:
            if p < market_price:
                i = 0
            if p > market_price:
                i = -1

        # if bid take right things
        if p <= market_price:
            res+=[volume[i+1]]

        if p > market_price:
            res+=[volume[i]]

    return (res,market_price)

def get_orderBook_data(price_interval = 0.05, len_bids_asks = 20):
    """Query order book data for all available

    price_interval --- percentage around the current market price to
    consider the orderBook

    len_bids_asks --- lengths of asks and bids output vectors

    """
    time_points = get_time_points()

    res=[]
    for time in time_points:
        print("Time: " + str(time))
        query = kraken._select_from_OrderBook(time,pair="XXBTZEUR")
        res += [process_orderbook(query,price_interval,len_bids_asks)]


    print("Saving results")
    with open("orderBook.json",'w') as ofile:
        json.dump(res, ofile)

