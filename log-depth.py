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

from kraken import Kraken, KrakenData

from multiprocessing import Pool

def f(what):
    if (what == "depth"):
        try:
            k.sync_OrderBook()
        except Exception as e:
            print("exception during depth sync",e)        
            return 0

    if (what == "trades"):
        try:
            k.sync_RecentTrades()
        except Exception as e:
            print("exception during trades sync",e)            
            return 0

    return what

def depth(pair):
    try:
        k.sync_OrderBook(pair)
    except Exception as e:
        print("exception during depth sync",e)
        return 0
    
    return pair

def trades(pair):
    try:
        k.sync_RecentTrades(pair)
    except Exception as e:
        print("exception during trades sync",e)
        return 0
    
    return pair


k = KrakenData(db_path="data/data.db", key_path="data/pi.key")

# pairs names
pairs = k._get_pairs()


pool = Pool(processes=2)

pool.map(f, ["depth","trades"])

pool.close()
pool.terminate()
pool.join()
