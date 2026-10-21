from datetime import datetime, time
import time as t

MARKET_OPEN = time(9, 0)
MARKET_CLOSE = time(23, 0)


def is_market_open():

    now = datetime.now().time()

    if MARKET_OPEN <= now <= MARKET_CLOSE:
        return True

    return False


def wait_until_market_opens():

    print("Market closed. Sleeping until market opens...")

    while True:

        now = datetime.now().time()

        if MARKET_OPEN <= now <= MARKET_CLOSE:
            print("Market open. Starting screener...\n")
            break

        t.sleep(60)