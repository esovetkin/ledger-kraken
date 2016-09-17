
-- drop all tables
DROP TABLE pairs;
DROP TABLE orderBook;
DROP TABLE orderBookLog;

-- creates a table with tradable pairs
CREATE TABLE pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name varchar(8) UNIQUE -- pair name, should be unique
                    );

-- fill table with tradable pairs
INSERT INTO pairs(name) VALUES ('XXLMXXBT');
INSERT INTO pairs(name) VALUES ('XXRPXXBT');
INSERT INTO pairs(name) VALUES ('XLTCXXBT');
INSERT INTO pairs(name) VALUES ('XETHXXBT');
INSERT INTO pairs(name) VALUES ('XETCXXBT');
INSERT INTO pairs(name) VALUES ('XDAOXXBT');
INSERT INTO pairs(name) VALUES ('XXDGXXBT');
INSERT INTO pairs(name) VALUES ('XXBTZEUR');
INSERT INTO pairs(name) VALUES ('XXBTZUSD');

-- creates a table with orders
CREATE TABLE orderBook
       (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       price REAL, -- price of the pair
       time INTEGER, -- time the order was created, get from kraken
       volume REAL, -- volume
       type varchar(4), -- type: bids/asks
       pair_id INTEGER, -- pair name
       FOREIGN KEY(pair_id) REFERENCES pairs(id),
       CONSTRAINT uc_orderID UNIQUE (price, time, volume, type, pair_id)
       );

-- index is needed to put orderBookLog
CREATE INDEX order_Index
ON orderBook (price, time, volume, type, pair_id)

-- creates a table with logs of 
CREATE TABLE orderBookLog
       (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       time INTEGER, -- time the info has been fetched
       order_id INTEGER, -- id of the order
       FOREIGN KEY(order_id) REFERENCES orders(id) 
       );      
