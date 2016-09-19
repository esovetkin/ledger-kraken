#!/bin/env python3

# This is part of kraken-tools
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import krakenex

import time

import sqlite3

from math import ceil


class Kraken(krakenex.API):
    """A wrap for the krakekex with API call rate control

    """
    
    def __init__(self, key = '', secret = '', conn = None, tier = 3):
        """Constructor for the child
        
        The most important part of initialising a child class is to
        set the tier. Different tier level implies different API call
        rate, see
        <https://www.kraken.com/help/api#api-call-rate-limit>

        """
        # call constructor of the parent
        super(Kraken, self).__init__(key = key, secret = secret, conn = conn)

        # set counter and timestamp
        self._counter = 0
        self._counter_time = time.time()

        if (tier not in [2,3,4]):
            raise Exception("Wrong tier number")
        
        self._tier = tier

        
    def _query_cost(self, urlpath):
        """Determines cost of the urlpath query

        urlpath --- path specified in _query

        return integer

        """

        # determine cost depending on the query
        if "private/Ledgers" in urlpath or "private/QueryLedgers" in urlpath or\
           "private/Trades" in urlpath or "private/QueryTrades" in urlpath:
            return 2
        elif "private/AddOrder" in urlpath or "private/CancelOrder" in urlpath:
            return 0
        else:
            return 1
        

    def _if_blocked(self):
        """Determines whether call rate limit is too high
        
        return True or False

        """

        # determine new counter: tier 2 users reduce count every 3
        # seconds, tier 3 users reduce count every 2 seconds, tier 4
        # users reduce count every 1 second.
        self._counter -= (time.time() - self._counter_time)/(4-(self._tier-1))

        # check if the counter is negative
        if (self._counter < 0):
            self._counter = 0
            
        self._counter_time = time.time()

        # determine if blocked
        if 2 == self._tier:
            return ceil(self._counter) >= 15
        elif 3 == self._tier or 4 == self._tier:
            return ceil(self._counter) >= 20

        
    def _query(self, urlpath, req = {}, conn = None, headers = {}):
        """Redefinition of low-level query handling

        Arguments correspond to the parent function.

        """
        
        # determine cost of the query and add up to the counter
        self._counter += self._query_cost(urlpath)
        
        while (self._if_blocked()):
            # print debug info
            print("blocked, counter = ",self._counter)
            # wait a second
            time.sleep(1)
            
            
        # call the parent function
        return super(Kraken, self)._query(urlpath = urlpath, req = req, \
                                          conn = conn, headers = headers)


class KrakenData(object):
    """Methods to access and store kraken data

    Data is stored in sqlite3 database. The following data can be
    downloaded and stored: historical order book, trades history,
    ledger, personal trades.

    """

    def __init__(self, db_path = '', key_path = ''):
        """Constructor

        Here we initialise database connection, kraken class to
        connect to exchange and other helping variables.

        db_path --- path for the database location
        key_path --- kraken key path

        """
        # init path for db and API keys
        self._db_path = db_path
        self._key_path = key_path
        
        # init db connection
        self._dbconn = sqlite3.connect(self._db_path)

        self._init_db()
        
        # init kraken connection
        self._kraken = Kraken()
        self._kraken.load_key(self._key_path)

        # get tradable pairs
        self._pairs = self._get_pairs()

        
    def _get_pairs(self):
        """Get tradable pairs

        The query is made from a table pairs from database

        return --- list of tradable pairs

        """
        c = self._dbconn.cursor()

        res = []
        try:
            for name in c.execute("SELECT name FROM pairs"):
                res.append(name[0])
        except Exception as e:
            print("Error on getting pair names",e)
            raise e

        return res

    
    def _init_db(self, path = "./createdb.sql"):
        """Initialising db by running a given sql-script
        
        path --- path to the script
        return --- nothing
        """
        c = self._dbconn.cursor()

        # try to read the file
        try:
            with open(path,'r') as f:
                script = f.read()
        except Exception as e:
            print("cannot read createdb.sql to variable",e)
            raise e

        # try to execute script with a database. Rollback in case of
        # errors
        try:
            c.executescript(script)
        except Exception as e:
            print("Error creating database",e)
            self._dbconn.rollback()
            raise e        

        self._dbconn.commit()

        
    def _get_ServerTime(self):
        """Get Kraken server time
        
        return --- float (actually, integer)

        """

        try:
            t = self._kraken.query_public("Time")

            if (len(t['error'])):
                raise Exception("API error", t['error'])
            
            t = t['result']
        except Exception as e:
            print("Error during API call: Time", e)
            raise e

        return t['unixtime']

    def _getTimeStamp(self, name):
        """Query timestamp name from the "timestamps" table

        name --- string of the timestamp name

        return --- float. "0" in case of absense of record

        """
        
        c = self._dbconn.cursor()

        # try to query timestamp
        try:
            c.execute("SELECT time FROM timestamps WHERE name = ?", (str(name),))
            return c.fetchone()[0]
        except Exception as e:
            print("Error during quering timestamp for '" + str(name) + "', ",e)
            print("Assuming timestamp is zero")
            return 0

        
    def _setTimeStamp(self, name, time):
        """Set a timestamp in the "timestamps" table
        
        name --- string of the timestamp name
        time --- new timestamp value

        return --- nothing

        """
        
        c = self._dbconn.cursor()

        # try to insert in timestamp
        try:
            c.execute("INSERT OR REPLACE INTO timestamps(time, name) VALUES (?,?)",
                      (time, name))
        except Exception as e:
            print("Error during inserting to timestamps",e)
            self._dbconn.rollback()
            raise e

        # commit changes in database
        self._dbconn.commit()

        
    def _insert_to_OrderBook(self, new_data, time):
        """Inserts to a database a given orderbook
        
        new_data --- a new entries orderbook 
        time --- timestamp of the orderbook download time

        """
        
        c = self._dbconn.cursor()
        
        # convert data to list
        orderbook_list = []
        orderbook_list2 = [] # TODO second list is redundant
        for pair, pairValue in new_data.items():
            for askbid, askbidValue in pairValue.items():
                for item in askbidValue:                
                    orderbook_list.append((item[0], item[2], askbid, item[1], pair))
                    orderbook_list2.append((item[2], time, item[0],
                                            item[2], askbid, item[1], pair))

        try: 
            # add orders
            c.executemany\
                ('''
                INSERT OR IGNORE INTO orderBook 
                (price, time, type, volume, pair_id) VALUES
                (?,?,?,?,
                (SELECT id from pairs WHERE name = ?))
                ''',
                 orderbook_list)
        
            # add time of fetch 
            c.executemany\
                ('''
                INSERT OR REPLACE INTO orderBookLog 
                (time_c, time_l, orderBook_id) VALUES
                (?,?,
                (SELECT id from orderBook WHERE price = ? AND time = ? AND 
                type = ? AND volume = ? AND 
                pair_id = (SELECT id from pairs WHERE name = ?) ))
                ''',
                 orderbook_list2)
        except Exception as e:
            print("Error with db insertion to ordersBook",e)
            self._dbconn.rollback()
            raise e

        # commit changes in database
        self._dbconn.commit()            


    def _insert_to_OrdersPrivate(self, new_data, time):
        """Insert new orders to the database

        new_data --- new data with orders
        time --- time the orders has been fetched (Kraken time)

        NOT FINISHED
        
        """

        c = self._dbconn.cursor()


        
        
        # update timestamp
        self._setTimeStamp("OrdersPrivate", time)
        
        # commit changes in database
        self._dbconn.commit()            
        
        
    def _sync_OrderBook(self, count = 500):
        """Download new order book for pairs given in self._pairs

        count --- number of entries in the order book to query 500
        (apparently current maximum for kraken is 500)

        """

        new_data = {}
        time = self._get_ServerTime()
        
        for pair in self._pairs:
            arg = {'pair': pair, 'count': count}

            # try API call
            try:
                t = self._kraken.query_public("Depth", arg)

                if (len(t['error'])):
                    raise Exception("API error", t['error'])

                t = t['result']
            except Exception as e:
                print("Error during API call: Depth for ", pair, e)
                raise e

            new_data[pair] = t[pair]

        self._insert_to_OrderBook(new_data,time)

        
    def _sync_OrdersPrivate(self):
        """Download open and closed orders and add them to the database

        NOT FINISHED

        """

        new_data = {}
        time = self._get_ServerTime()

        # determine time period for the closed order to query
        start = self._queryTimeStamp("OrdersPrivate")
        end = time
        
        # try API call
        try:
            # query OpenOrders
            t = self._kraken.query_private("OpenOrders")

            if (len(t['error'])):
                raise Exception("API error", t['error'])

            t = t['result']['open']
            
            arg = {'start': start, 'end': end}

            # query ClosedOrders (until the timestamp time)
            
        except Exception as e:
            print("Error during API call: Open- Closed- Orders", e)
            raise e

        # update database
        self._insert_to_OrdersPrivate(new_data, time)

        
