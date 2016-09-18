-- creates a table with tradable pairs
CREATE TABLE IF NOT EXISTS pairs (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name varchar(8) UNIQUE                -- pair name, should be unique
);

-- creates a table with orders
CREATE TABLE IF NOT EXISTS orderBook
(
id INTEGER PRIMARY KEY AUTOINCREMENT,
price REAL,                               -- price of the pair
time INTEGER,                             -- time the order was created, get from kraken
volume REAL,                              -- volume
type varchar(4),                          -- type: bids/asks
pair_id INTEGER,                          -- pair name
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
time_c INTEGER,                                   -- first time the order was seen
time_l INTEGER,                                   -- last time the order was seen
orderBook_id INTEGER,                             -- id of the order book entry
FOREIGN KEY(orderBook_id) REFERENCES orderBook(id),
CONSTRAINT uc_logID UNIQUE (orderBook_id)
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
ordertxid varchar(19),                    -- order responsible for execution of trade
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

-- table for storing description of orders
CREATE TABLE IF NOT EXISTS descriptionOrders
(
id INTEGER PRIMARY KEY AUTOINCREMENT,
pair varchar(6),                          -- asset pair
leverage varchar(25),                     -- amount of leverage
order varchar(255),                       -- order description
ordertype varchar(255),                   -- order type 
price REAL,                               -- primary price
price2 REAL,                              -- secondary price
type varchar(25),                         -- type of order (buy/sell)
close varchar(255)                        -- conditional close order description (if conditional close set)
);

-- table for stoting orders
CREATE TABLE IF NOT EXISTS ordersPrivate
(
id INTEGER PRIMARY KEY AUTOINCREMENT,
orderxid varchar(19),                     -- Referral order transaction id that created this order
userref varchar(255),                     -- user reference id
status varchar(25),                       -- status of order:
                                          --    pending = order pending book entry,
                                          --    open = open order
                                          --    closed = closed order
                                          --    canceled = order canceled
                                          --    expired = order expired
opentm REAL,                              -- unix timestamp of when order was placed
starttm REAL,                             -- unix timestamp of order start time (or 0 if not set)
expiretm REAL,                            -- unix timestamp of order end time (or 0 if not set)
closetm REAL,                             -- unix timestamp of when order was closed
closereason varchar(255)                  -- amount of available order info matching criteria
descr INTEGER,                            -- order description info
vol REAL,                                 -- volume of order (base currency unless viqc set in oflags)
vol_exec REAL,                            -- volume executed (base currency unless viqc set in oflags)
cost REAL,                                -- total cost (quote currency unless unless viqc set in oflags)
fee REAL,                                 -- total fee (quote currency)
price REAL,                               -- average price (quote currency unless viqc set in oflags)
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
FOREIGN KEY(descr) REFERENCES  descriptionOrders(id),
CONSTRAINT uc_orderid UNIQUE (orderxid)
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

-- fill table with tradable pairs
INSERT OR IGNORE INTO pairs(name) VALUES ('XXBTZEUR');
INSERT OR IGNORE INTO pairs(name) VALUES ('XXBTZUSD');
INSERT OR IGNORE INTO pairs(name) VALUES ('XXBTZJPY');
INSERT OR IGNORE INTO pairs(name) VALUES ('XXBTZGBP');
INSERT OR IGNORE INTO pairs(name) VALUES ('XXBTZCAD');

INSERT OR IGNORE INTO pairs(name) VALUES ('XDAOXETH');
INSERT OR IGNORE INTO pairs(name) VALUES ('XDAOXXBT');
INSERT OR IGNORE INTO pairs(name) VALUES ('XDAOZCAD');
INSERT OR IGNORE INTO pairs(name) VALUES ('XDAOZEUR');
INSERT OR IGNORE INTO pairs(name) VALUES ('XDAOZGBP');
INSERT OR IGNORE INTO pairs(name) VALUES ('XDAOZJPY');
INSERT OR IGNORE INTO pairs(name) VALUES ('XDAOZUSD');

INSERT OR IGNORE INTO pairs(name) VALUES ('XETCXETH');
INSERT OR IGNORE INTO pairs(name) VALUES ('XETCXXBT');
INSERT OR IGNORE INTO pairs(name) VALUES ('XETCZEUR');
INSERT OR IGNORE INTO pairs(name) VALUES ('XETCZUSD');

INSERT OR IGNORE INTO pairs(name) VALUES ('XETHXXBT');
INSERT OR IGNORE INTO pairs(name) VALUES ('XETHZCAD');
INSERT OR IGNORE INTO pairs(name) VALUES ('XETHZEUR');
INSERT OR IGNORE INTO pairs(name) VALUES ('XETHZGBP');
INSERT OR IGNORE INTO pairs(name) VALUES ('XETHZJPY');
INSERT OR IGNORE INTO pairs(name) VALUES ('XETHZUSD');

INSERT OR IGNORE INTO pairs(name) VALUES ('XLTCXXBT');
INSERT OR IGNORE INTO pairs(name) VALUES ('XLTCZCAD');
INSERT OR IGNORE INTO pairs(name) VALUES ('XLTCZEUR');
INSERT OR IGNORE INTO pairs(name) VALUES ('XLTCZUSD');

INSERT OR IGNORE INTO pairs(name) VALUES ('XXDGXXBT');        
INSERT OR IGNORE INTO pairs(name) VALUES ('XXLMXXBT');
INSERT OR IGNORE INTO pairs(name) VALUES ('XXRPXXBT');


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
