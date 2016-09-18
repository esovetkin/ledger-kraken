#!/bin/env python3

from kraken import Kraken

import sqlite3

# class Asset(object):
#     """Class containing one asset

#     """

#     def __init__(self, amount, pair, stategy)

# class Order(object):
#     """Class where all the order information is stored
#     """

#     def __init__(self, price, volume, ):
#         self._orderid = orderid

class KrakenData(object):
    """Methods to access and store kraken data

    Data is stored in sqlite3 database. The following data can be
    downloaded and stored: historical order book, trades history,
    ledger, personal trades.

    """

    def __init__(self, db_path = '', key_path = ''):
        # init path for db and API keys
        self._db_path = db_path
        self._key_path = key_path
        
        # init db connection
        self._dbconn = sqlite3.connect(self._db_path)

        # init kraken connection
        self._kraken = Kraken()
        self._kraken.load_key(self._key_path)

        # tradable pairs
        self._pairs = ["XXLMXXBT","XXRPXXBT","XLTCXXBT","XETHXXBT","XETCXXBT",
                       "XDAOXXBT","XXDGXXBT","XXBTZEUR","XXBTZUSD"]
        

    def _init_db(self):
        """Initialising db at a given path by running a sql-script        
        """
        c = self._dbconn.cursor()

        script = '''        
        -- creates a table with tradable pairs
        CREATE TABLE IF NOT EXISTS pairs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name varchar(8) UNIQUE -- pair name, should be unique
        );

        -- fill table with tradable pairs
        INSERT OR IGNORE INTO pairs(name) VALUES ('XXLMXXBT');
        INSERT OR IGNORE INTO pairs(name) VALUES ('XXRPXXBT');
        INSERT OR IGNORE INTO pairs(name) VALUES ('XLTCXXBT');
        INSERT OR IGNORE INTO pairs(name) VALUES ('XETHXXBT');
        INSERT OR IGNORE INTO pairs(name) VALUES ('XETCXXBT');
        INSERT OR IGNORE INTO pairs(name) VALUES ('XDAOXXBT');
        INSERT OR IGNORE INTO pairs(name) VALUES ('XXDGXXBT');
        INSERT OR IGNORE INTO pairs(name) VALUES ('XXBTZEUR');
        INSERT OR IGNORE INTO pairs(name) VALUES ('XXBTZUSD');

        CREATE INDEX IF NOT EXISTS pairs_Index ON pairs (name);

        -- creates a table with orders
        CREATE TABLE IF NOT EXISTS orderBook
        (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        price REAL, -- price of the pair
        time INTEGER, -- time the order was created, get from kraken
        volume REAL, -- volume
        type varchar(4), -- type: bids/asks
        pair_id INTEGER, -- pair name
        FOREIGN KEY(pair_id) REFERENCES pairs(id),
        CONSTRAINT uc_orderID UNIQUE (price, time, type, volume, pair_id)
        );

        -- index is needed to put orderBookLog
        CREATE INDEX IF NOT EXISTS orders_Index
        ON orderBook (price, time, volume, type, pair_id);

        -- creates a table with logs of order Book orders
        -- The data is stored in the following format:
        --
        -- Creation time | Last time seen | Order Id
        --

        -- This structure will allow to reduce the size of database,
        -- since only the changes are stored. The only problem
        -- appeares with the orders which are at the lower border of
        -- the orderBook, since in case of increase of amount of
        -- orders, the Last time seen will not be updated until the
        -- amount of orders reduced to the previous amount (due to the
        -- limitation of kraken, 500 orders).
        CREATE TABLE IF NOT EXISTS orderBookLog
        (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time_c INTEGER, -- first time the order was seen
        time_l INTEGER, -- last time the order was seen
        orderBook_id INTEGER, -- id of the order book entry
        FOREIGN KEY(orderBook_id) REFERENCES orderBook(id)
        CONSTRAINT uc_logID UNIQUE (orderBook_id)
        );      

        CREATE INDEX IF NOT EXISTS orderid_Index
        ON orderBookLog (orderBook_id);
        '''
        
        try:
            c.executescript(script)
        except Exception as e:
            print("Error creating database",e)
            self._dbconn.rollback()
            raise e        

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
            print("Error with db insertion",e)
            self._dbconn.rollback()
            raise e

        # commit changes in database
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
            
        
    def _sync_OrderBook(self, count = 500):
        """Download new order book for pairs given in self._pairs

        count --- number of entries in the order book to query 500
        (apparently current maximum for kraken)
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

    
