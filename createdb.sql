-- This is part of kraken-tools
--
-- This program is free software: you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation, either version 3 of the License, or
-- (at your option) any later version.
--
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.
--
-- You should have received a copy of the GNU General Public License
-- along with this program.  If not, see <http://www.gnu.org/licenses/>.


-- create table with timestamps of the syncronisation times (this
-- table is unrelated with the kraken data). It is used for the
-- internal purposes.
CREATE TABLE IF NOT EXISTS timestamps
(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name varchar(25) NOT NULL,                -- name of the synchronisation 
time REAL NOT NULL,                       -- time of the last synchronisation
CONSTRAINT uc_name UNIQUE (name)
);

-- creates a table with tradable pairs
CREATE TABLE IF NOT EXISTS pairs
(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name varchar(8) NOT NULL,                  -- pair name, should be unique
altname varchar(6),                        -- alternate pair name
aclass_base varchar(25),                   -- asset class of base component
base varchar(4) NOT NULL,                  -- asset id of base component
aclass_quote varchar(10),                  -- asset class of quote component
quote varchar(4) NOT NULL,                 -- asset id of quote component
lot varchar(25),                           -- volume lot size
pair_decimals INTEGER,                     -- scaling decimal places for pair
lot_decimals INTEGER,                      -- scaling decimal places for volume
lot_multiplier REAL,                       -- amount to multiply lot volume by to get currency volume
-- leverage_buy ???                           -- array of leverage amounts available when buying
-- leverage_buy ???                           -- array of leverage amounts available when selling
-- fees ???                                   -- fee schedule array in [volume, percent fee] tuples
-- fees_makes ???                             -- maker fee schedule array in [volume, percent fee] tuples (if on maker/taker)
-- fee_volume_currency ???                    -- volume discount currency
margin_call REAL,                          -- margin call level
margin_stop REAL,                          -- stop-out/liquidation margin level
CONSTRAINT uc_name UNIQUE (name, base, quote)
);

-- creates a table with orders
CREATE TABLE IF NOT EXISTS orderBook
(
id INTEGER PRIMARY KEY AUTOINCREMENT,
price REAL NOT NULL,                      -- price of the pair
time INTEGER NOT NULL,                    -- krakentime the order was created
volume REAL NOT NULL,                     -- volume
type varchar(4) NOT NULL,                 -- type: bids/asks
pair_id INTEGER NOT NULL,                 -- pair name
FOREIGN KEY(pair_id) REFERENCES pairs(id),
CONSTRAINT uc_orderID UNIQUE (price, time, type, volume, pair_id)
);

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
time_c INTEGER NOT NULL,                  -- first time the order was seen
time_l INTEGER NOT NULL,                  -- last time the order was seen
orderBook_id INTEGER NOT NULL,            -- id of the order book entry
FOREIGN KEY(orderBook_id) REFERENCES orderBook(id),
CONSTRAINT uc_logID UNIQUE (orderBook_id)
);      


-- table for stoting orders
CREATE TABLE IF NOT EXISTS ordersPrivate
(
id INTEGER PRIMARY KEY AUTOINCREMENT,
orderxid varchar(19) NOT NULL,            -- Referral order transaction id that created this order
userref varchar(255),                     -- user reference id
status varchar(25) NOT NULL,              -- status of order:
                                          --    pending = order pending book entry,
                                          --    open = open order
                                          --    closed = closed order
                                          --    canceled = order canceled
                                          --    expired = order expired
opentm REAL NOT NULL,                     -- unix timestamp of when order was placed
starttm REAL,                             -- unix timestamp of order start time (or 0 if not set)
expiretm REAL,                            -- unix timestamp of order end time (or 0 if not set)
closetm REAL,                             -- unix timestamp of when order was closed
closereason varchar(255),                 -- amount of available order info matching criteria
descr_pair varchar(6) NOT NULL,           -- asset pair
descr_leverage varchar(25),               -- amount of leverage
descr_order varchar(255) NOT NULL,        -- order description
descr_ordertype varchar(255) NOT NULL,    -- order type 
descr_price REAL,                         -- primary price (might be null in case of market type)
descr_price2 REAL,                        -- secondary price
descr_type varchar(25) NOT NULL,          -- type of order (buy/sell)
descr_close varchar(255),                 -- conditional close order description (if conditional close set)
vol REAL NOT NULL,                        -- volume of order (base currency unless viqc set in oflags)
vol_exec REAL NOT NULL,                   -- volume executed (base currency unless viqc set in oflags)
cost REAL,                                -- total cost (quote currency unless unless viqc set in oflags)
fee REAL NOT NULL,                        -- total fee (quote currency)
price REAL NOT NULL,                      -- average price (quote currency unless viqc set in oflags)
stopprice REAL,                           -- stop price (quote currency, for trailing stops)
limitprice REAL,                          -- triggered limit price (quote currency, when limit based order type triggered)
misc varchar(255),                        -- comma delimited list of miscellaneous info
                                          --   stopped = triggered by stop price
                                          --   touched = triggered by touch price
                                          --   liquidated = liquidation
                                          --   partial = partial fill
oflags varchar(255),                      -- comma delimited list of order flags
                                          --   viqc = volume in quote currency
                                          --   fcib = prefer fee in base currency (default if selling)
                                          --   fciq = prefer fee in quote currency (default if buying)
                                          --   nompp = no market price protection
trades varchar(255),                      -- array of trade ids related to order (if trades info requested and data available) TODO that is an array?
CONSTRAINT uc_orderid UNIQUE (orderxid)
);

-- table for storing private trades entries
CREATE TABLE IF NOT EXISTS tradesPrivate
(
id INTEGER PRIMARY KEY AUTOINCREMENT,
refid varchar(19),                        -- trade id string
cost REAL,                                -- total cost of order (quote currency)
fee REAL,                                 -- total fee (quote currency)
margin REAL,                              -- initial margin (quote currency)
misc varchar(255),                        -- comma delimited list of miscellaneous info
                                          --   closing = trade closes all or part of a position
orderxid varchar(19),                     -- order responsible for execution of trade
ordertype varchar(255),                   -- order type
pair varchar(8),                          -- asset pair
price REAL,                               -- average price order was executed at (quote currency)
time REAL,                                -- unix timestamp of trade
type varchar(25),                         -- type of order (buy/sell)
vol REAL,                                 -- volume (base currency)
posstatus varchar(25),                    -- position status (open/closed)
cprice REAL,                              -- average price of closed portion of position (quote currency)
ccost REAL                                -- total cost of closed portion of position (quote currency)
cfee REAL,                                -- total fee of closed portion of position (quote currency)
cvol REAL,                                -- total fee of closed portion of position (quote currency)
cmargin REAL,                             -- total margin freed in closed portion of position (quote currency)
net REAL,                                 -- net profit/loss of closed portion of position (quote currency, quote currency scale)
trades varchar(255),                      -- list of closing trades for position (if available)
CONSTRAINT uc_tradeid UNIQUE (refid),
FOREIGN KEY(orderxid) REFERENCES ordersPrivate(orderxid)
);


-- table for storing ledger entries
CREATE TABLE IF NOT EXISTS ledger
(
id INTEGER PRIMARY KEY AUTOINCREMENT,
aclass varchar(25),                       -- only 'currency' according to kraken.com/help/api
ledgerid varchar(19),                     -- ledger id string
refid varchar(19),                        -- trade id string
amount REAL,                              -- transaction amount
fee REAL,                                 -- transaction fee
asset varchar(4),                         -- e.g. XXBT
balance REAL,                             -- resulting balance
time REAL,                                -- unix timestamp of ledger
type varchar(25),                         -- type of ledger entry (deposit, withdrawal, trade, margin)
CONSTRAINT uc_ledgerid UNIQUE (ledgerid),
FOREIGN KEY(refid) REFERENCES tradesPrivate(refid)
);


-- index is needed to search among the names of tradable pairs
CREATE INDEX IF NOT EXISTS pairs_Index ON pairs (name);

-- index is needed to search orderBook_id
CREATE INDEX IF NOT EXISTS orderid_Index
ON orderBookLog (orderBook_id);

-- index is needed to search in descriptionOrders
CREATE INDEX IF NOT EXISTS descrid_Index
ON orderBookLog (id);

-- index is needed to efficiently put id of the orderBook to orderBookLog
CREATE INDEX IF NOT EXISTS orders_Index
ON orderBook (price, time, volume, type, pair_id);
