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
    
    def __init__(self, key = '', secret = '', conn = None, tier = 3, db_path = "/tmp/kraken_counter.db"):
        """Constructor for the child
        
        The most important part of initialising a child class is to
        set the tier. Different tier level implies different API call
        rate, see
        <https://www.kraken.com/help/api#api-call-rate-limit>

        key, secret, conn --- parameters for the krakenex.API constructor

        tier --- kraken tier (possible values 2,3 or 4). Exception otherwise

        db_path --- path to the database where the current counter is
        stored. DB support allows to run several instances and have
        inter-process communications (at least among the processes
        that share the common database), so that the queries rate call
        is not too high.
        """
        # call constructor of the parent
        super(Kraken, self).__init__(key = key, secret = secret, conn = conn)
        
        # set up a database for storing counter and counter_time
        self._dbconn = sqlite3.connect(db_path, timeout = 5, isolation_level="EXCLUSIVE")
        
        # set tier level
        if (tier not in [2,3,4]):
            raise Exception("Wrong tier number")
        
        self._tier = tier
    
        # init database
        self._init_db()
        
        # counter_diff is used to update the counter correctly inside
        # a database
        self._counter_diff = 0

        # we keep the latest values of the counter. actually it can be
        # removed (only for debugging purposes)
        self._counter = 0;
        self._counter_time = 0;


        
    def _init_db(self):
        """Create a database with a single table and a single row which
        contains information about the counter and the timestamp the
        counter was made

        The aim of the database is to take advatage of the sqlite lock
        system for interprocess communications.
        """
        
        # try to create a table
        try:
            c = self._dbconn.execute('''BEGIN EXCLUSIVE''')
                        
            # as a timestamp for the counter we use system time
            # (time.time()). Mostly, for other timestamps we use
            # kraken time. It might be an option to replace system
            # time with Kraken time, but in that case one has to set
            # counter not to zero. Anyway, at the current point it
            # seems to be a reasonable solution.
            c.execute('''
            CREATE TABLE IF NOT EXISTS counter
            (
            Lock char(1) NOT NULL DEFAULT 'X',
            counter REAL NOT NULL,
            time REAL NOT NULL,
            CONSTRAINT pk_Lock PRIMARY KEY (Lock),
            CONSTRAINT ck_Lock_Locked CHECK (Lock = 'X')
            )''')

            # set the table wiith default values
            c.execute('''
            INSERT OR IGNORE INTO counter 
            (counter, time) VALUES
            (0, ?)''', (time.time(),))

            # commit changes in database
            self._dbconn.commit()            
        except Exception as e:
            print("Error creating database (kraken counter)",e)
            self._dbconn.rollback()
            raise e                    
        
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

        The functions calls the database and updates its values
        
        return True or False. True if call rate is too high

        """

        try:
            c = self._dbconn.execute('''BEGIN EXCLUSIVE''')

            c.execute("SELECT counter, time FROM counter")
            self._counter, self._counter_time = c.fetchone()
            
            # determine new counter: tier 2 users reduce count every 3
            # seconds, tier 3 users reduce count every 2 seconds, tier
            # 4 users reduce count every 1 second.
            self._counter -= (time.time() - self._counter_time)/(4-(self._tier-1))
        
            # check if the counter is negative
            if (self._counter < 0):
                self._counter = 0
            
            # update value with the new query cost
            self._counter += self._counter_diff
            self._counter_time = time.time()
            
            self._counter_diff = 0

            # write updated values
            c.execute('''
            INSERT OR REPLACE INTO counter
            (counter, time) VALUES
            (?, ?)''', (self._counter, self._counter_time))

            # commit changes
            self._dbconn.commit()
        except Exception as e:
            print("Error db, while getting counter",e)
            self._dbconn.rollback()
            raise e
            
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
        self._counter_diff = self._query_cost(urlpath)
        
        while (self._if_blocked()):
            # print debug info
            print("blocked, counter = ",self._counter)
            # wait a second
            time.sleep(5)
            
        # call the parent function
        return super(Kraken, self)._query(urlpath = urlpath, req = req, \
                                          conn = conn, headers = headers)


class KrakenData(object):
    """Methods to access and store kraken data

    Data is stored in sqlite3 database. The following data can be
    downloaded and stored: historical order book, trades history,
    ledger, personal trades.

    """

    def __init__(self, db_path = '', key_path = '', tier = 3):
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
        
        # init kraken connection
        self._kraken = Kraken(tier = tier)
        self._kraken.load_key(self._key_path)

        # init database
        self._init_db()
        
        
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

    def _init_pairs(self):
        """Download from Kraken tradable pairs and insert them to table pairs
        in database

        """

        # try to download tradable pairs
        try:
            t = self._kraken.query_public("AssetPairs")

            if (len(t['error'])):
                raise Exception("API error", t['error'])
            
            t = t['result']
        except Exception as e:
            print("Error during API call: AssetsPairs", e)
            raise e

        c = self._dbconn.cursor()

        pairs = []
        for name, v in t.items():
            # hmm, there are some pairs with ".d" suffix. I don't know
            # what they mean, so we simply ignore them
            if (len(name) == 8):
                pairs.append((name, v['altname'], v['aclass_base'], v['base'],
                              v['aclass_quote'], v['quote'], v['lot'], v['pair_decimals'],
                              v['lot_decimals'], v['lot_multiplier'], v['margin_call'],
                              v['margin_stop']))

        # try to insert data to the database
        try:
            c.executemany('''
            INSERT INTO pairs
            (name, altname, aclass_base, base, aclass_quote, quote, lot, pair_decimals,
            lot_decimals, lot_multiplier, margin_call, margin_stop)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ''', pairs)
        except Exception as e:
            print("Error with db insertion to pairs",e)
            self._dbconn.rollback()
            raise e

        # commit changes
        self._dbconn.commit()

        
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

        # if tables pairs is empty fill it with data from kraken
        if (len(self._get_pairs()) == 0):
            self._init_pairs()

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

    def _insert_to_Trades(self, new_data):
        """Inserts to a database recent trades

        new_data --- recent trades dictionary

        """

        c = self._dbconn.cursor()

        # convert data to a list
        trades_list = []
        for pair, pairValue in new_data.items():
            for item in pairValue:
                trades_list.append((pair, item[0], item[1],
                                    item[2], item[3], item[4], item[5]))

        try:
            c.executemany('''
            INSERT OR REPLACE INTO trades
            (pair_id, price, volume, time, buysell, type, misc) VALUES
            ((SELECT id from pairs WHERE name = ?),
            ?,?,?,?,?,?)
            ''', trades_list)

        except Exception as e:
            print("Error with db insertion to trades",e)
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
        
        # convert data to a list
        orderbook_list = []
        for pair, pairValue in new_data.items():
            for askbid, askbidValue in pairValue.items():
                for item in askbidValue:                
                    orderbook_list.append((item[0], item[2], time, askbid, item[1], pair))

        try: 
            # add orders
            c.executemany('''
            INSERT OR REPLACE INTO orderBook 
            (price, time, time_l, type, volume, pair_id) VALUES
            (?,?,?,?,?,
            (SELECT id from pairs WHERE name = ?))
            ''', orderbook_list)
        
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

        NOT TESTED
        
        """

        c = self._dbconn.cursor()

        # convert data to list
        order_list = []
        for orderid,v in new_data.items():
            order_list.append(orderid, v['userref'], v['status'],
                              v['opentm'],v['starttm'],v['expiretm'],
                              v['closetm'],v['closereason'],
                              v['descr']['pair'],v['descr']['leverage'],
                              v['descr']['order'],v['descr']['ordertype'],
                              v['descr']['price'],v['descr']['price2'],
                              v['descr']['type'],v['descr']['close'],
                              v['vol'],v['vol_exec'],v['cost'],
                              v['fee'],v['price'],
                              v['stopprice'],v['limitprice'],v['misc'],
                              v['oflags'],v['trades'],v['descr']['pair'])

        try:
            c.executemany('''
            INSERT OR REPLACE INTO ordersPrivate
            (orderxid, userref, status, opentm, starttm, expiretm, closetm,
            closereason, descr_pair, descr_leverage, descr_order, descr_ordertype,
            descr_price, descr_price2, descr_type, descr_close, vol, vol_exec,
            cost, fee, price, stopprice, limitprice, misc, oflags, trades, pair_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
            SELECT id FROM pairs WHERE altname = ?)
            ''',
            order_list)
        except Exception as e:
            print("Error with db insertion to ordersPrivate",e)
            self._dbconn.rollback()
            raise e
        
        # update timestamp
        self._setTimeStamp("OrdersPrivate", time)
        
        # commit changes in database
        self._dbconn.commit()            


    def _insert_to_TradesPrivate(self, new_data, time):
        """Insert new private trades to the database
        
        new_data --- new data with orders
        time --- time the trades has been fetched (Kraken time)

        NOT TESTED

        """

        c = self._dbconn.cursor()

        # convert data to list
        trade_list = []
        for refid,v in new_data.items():
            trade_list.append(refid, v['cost'],v['fee'],v['margin'],
                              v['misc'],v['ordertype'],
                              v['pair'],v['price'],v['time'],v['type'],
                              v['vol'], v['posstatus'],v['cprice'],v['ccost'],
                              v['cfee'],v['cvol'],v['cmargin'],v['net'],v['trades'],
                              v['orderxid'],v['pair'])

        try:
            c.executemany('''
            INSERT INTO tradesPrivate
            (refid, cost, fee, margin, misc, orderxid, ordertype, pair,
            price, time, type, vol, possstatus, cprice, ccost, cfee, cvol,
            cmargin, net, trades)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
            SELECT orderxid FROM ordersPrivate WHERE orderxid = ?,
            SELECT id FROM pairs WHERE name = ?)
            ''',
             trade_list)
        except Exception as e:
            print("Error with db insertion to tradesPrivate",e)
            self._dbconn.rollback()
            raise e

        # update timestamp
        self._setTimeStamp("tradesPrivate", time)

        # commit changes in database
        self._dbconn.commit()


    def _insert_to_ledger(self, new_data, time):
        """Insert new ledger entries to the database

        new_data --- new data with ledger entries
        time --- time the ledger has been fetched (Kraken time)

        NOT TESTED

        """

        c = self._dbconn.cursor()

        # convert data to list
        ledger_list = []
        for ledgerid, v in new_data.items():
            ledger_list.append(ledgerid, v['aclass'], v['refid'],v['amount'],
                               v['fee'],v['asset'],v['balance'],v['time'],v['type'])

        try:
            c.executemany('''
            INSERT OR REPLACE INTO ledger
            (ledgerid, aclass, refid, amount, fee, asset, balance, time, type)
            VALUES (?,?,?,?,?,?,?,?,?)
            ''',
             ledger_list)
        except Exception as e:
            print("Error with db insertion to ledger",e)
            self._dbconn.rollback()
            raise e

        # update timestamp
        self._setTimeStamp("ledger", time)

        # commit changes in database
        self._dbconn.commit()
        

    def sync_RecentTrades(self, pair):
        """Download recent trades data

        Downloads recent trades data for every tradable pair. Store
        the timestamp of the fetch time in the database.

        pair --- a tradable pair name
        """

        # recent trades data
        new_data = {}
        # corresponding to pair timestamps. In is better to store this
        # as a list and insert to a database only after successful
        # fetch and insertion of the actual trades.
        timestamps = {}

        arg = {"pair":pair, "since": self._getTimeStamp("RecentTrades-" + pair)}

        # try API call
        try:
            t = self._kraken.query_public("Trades", arg)
            
            if (len(t['error'])):
                raise Exception("API error", t['error'])
            
            t = t['result']
        except Exception as e:
            print("Error during API call: Depth for ", pair, e)
            print("Skipping pair:", pair)
            continue

        # new_data and timestamps are appended only in case
        # successful query
        new_data[pair] = t[pair]
        timestamps[pair] = t['last']
        
        # insert data to a databaase
        self._insert_to_Trades(new_data)

        # update timestamps (this line is reached only in case of
        # successful insertion of data). The following insertion is
        # not as complicated as the previous one (less chance to get
        # mistake).
        for pair,time in timestamps.items():
            self._setTimeStamp("RecentTrades-" + pair, time)

            
    def sync_OrderBook(self, pair, count = 500):
        """Download new order book for pairs given in self._pairs

        count --- number of entries in the order book to query 500
        (apparently current maximum for kraken is 500)
        
        pair --- a tradable pair name

        """

        new_data = {}
        time = self._get_ServerTime()
        
        arg = {'pair': pair, 'count': count}

        # try API call
        try:
            t = self._kraken.query_public("Depth", arg)
            
            if (len(t['error'])):
                raise Exception("API error", t['error'])
            
            t = t['result']
        except Exception as e:
            print("Error during API call: Depth for ", pair, e)
            print("Skipping pair:", pair)
            continue

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

