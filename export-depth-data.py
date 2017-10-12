#!/bin/env python3

from kraken import Kraken, KrakenData
import numpy as np

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


res = get_time_points()
