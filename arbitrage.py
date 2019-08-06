#!/bin/python

from kraken import Kraken
from functions import \
    query_tradable_pairs, \
    get_pairs_names, \
    query_orderbook, \
    depth_matrix, \
    approximate_depth_matrix, \
    save_lp

if __name__ == '__main__':
    kraken = Kraken()
    kraken.load_key("keys/albus.key")

    pairs = query_tradable_pairs(kraken)
    pair_names = get_pairs_names(pairs)
    orderbook = query_orderbook(kraken, pair_names)

    prices = depth_matrix(orderbook, pairs)
    #prices = approximate_depth_matrix(prices)

    save_lp(prices, "problem.lp")


