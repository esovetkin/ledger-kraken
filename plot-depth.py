#!/bin/env python3

from kraken import Kraken, KrakenData

from matplotlib import pyplot as plt
from matplotlib import animation
import numpy as np

kraken = KrakenData(db_path="data/data.db",key_path="keys/albus.key")

def query_cumsum(depth_res, interval=(0.8,1.2)):
    """Convert query result to the cumsum of bids and asks

    depth_res --- result of the query
    
    """
    # get asks and bids from queried data
    asks = list(filter(lambda x: x[2] == "asks", depth_res))
    bids = list(filter(lambda x: x[2] == "bids", depth_res))
    
    # sort by price
    asks = sorted(asks, key=lambda x: x[0])
    bids = sorted(bids, key=lambda x: -x[0])

    # calculate accumulated volume and corresponding price
    volume = list(np.cumsum([float(x[1]) for x in bids]))[::-1] + list(np.cumsum([float(x[1]) for x in asks]))
    price = list([float(x[0]) for x in bids])[::-1] + list([float(x[0]) for x in asks])

    # get market price (average between largest bids and smallest asks)
    market_price=(max([float(x[0]) for x in bids]) + min([float(x[0]) for x in asks]))/2
    
    # plot only +/- 20% around the market price
    pr_vol = list(zip(price,volume))
    volume=[v for p,v in pr_vol if p > interval[0]*market_price and p < interval[1]*market_price]
    price=[p for p,v in pr_vol if p > interval[0]*market_price and p < interval[1]*market_price]
    
    return (price, volume)

def plot_time(time):
    query = kraken._select_from_OrderBook(time,pair="XXBTZEUR")
    price,volume = query_cumsum(query)
    plt.plot(price,volume)
    plt.show()

fig = plt.figure()
ax = plt.axes(xlim=(300,1500),ylim=(0,5000))
line, = ax.plot([],[])

def init():
    line.set_data([],[])
    return line,

def animate(i):
    print("Iteration: " + str(i))
    # query depth book 
    query = kraken._select_from_OrderBook(1480201200+i*300,pair="XXBTZEUR")

    # calculate accumulated price and volume
    price,volume = query_cumsum(query)

    # update plot
    line.set_data(price, volume)
    
    return line,
    
anim = animation.FuncAnimation(fig,animate,init_func=init,
                               frames=8640,interval=200,blit=True)

anim.save('basic_animation.mp4', fps=12, extra_args=['-vcodec', 'libx264'])

#plt.show()
