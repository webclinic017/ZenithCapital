import math
import asyncio
from ib_insync import *
from config import *
from sheets import get_points_and_settings
from datetime import datetime, timedelta, timezone

# connect to IBKR
util.startLoop()
ib = IB()
ib.connect("127.0.0.1", TWS_PORT, clientId=1)


def get_history(contracts):
    """A function to return the price history of any given contracts

    Args:
      contracts ([Contract]): List of contracts to get history for

    Returns:
      Dict<String, [Float]>: Dictionary of contract symbols and their prices
    """

    history = {}
    for contract in contracts:
        # 30 second candles for the past X seconds

        bars = ib.reqHistoricalData(contract, endDateTime="",
                                    durationStr=str(HISTORY_LOOKBACK) + " S",
                                    barSizeSetting="30 secs",
                                    whatToShow="MIDPOINT",
                                    useRTH=True, formatDate=1)

        history[contract.symbol] = [bar.close for bar in bars]

    return history


def pearson(x):
    """A function to calculate the pearson correlation coefficient

    Args:
        x ([Float]): List of prices

    Returns:
        Float: Pearson correlation coefficient
    """
    y = [i for i in range(len(x))]

    avg_x = sum(x)/len(x)
    avg_y = sum(y)/len(y)

    sxy = sum([(xi - avg_x) * (yi - avg_y) for xi, yi in zip(x, y)])
    sxx = sum([(xi - avg_x) ** 2 for xi in x])
    syy = sum([(yi - avg_y) ** 2 for yi in y])

    if sxx * syy == 0:
        return 0

    r = sxy / (sxx * syy) ** 0.5
    return r


def place_order(action, contract, quantity, price):
    """A function to place a bracket order through IBKR

    Args:
        action (String): "BUY" or "SELL"
        contract (Contract): IBKR Contract
        quantity (Float): Number of shares to buy or sell
        price (Float): Price to buy or sell at

    Returns:
        Order: The limit order placed
    """
    trades = ib.trades()

    for trade in trades:

        # if similar order (same symobl, action, and price)
        if trade.contract.symbol == contract.symbol and trade.order.action == action \
        and len(trade.fills) > 0 and trade.order.lmtPrice == price:
            order_time = trade.fills[0].execution.time
            time_ago = (datetime.now(timezone.utc) -
                        order_time).total_seconds()

            # if order was filled within past 2 minutes ago, stop placing order
            if time_ago < 120:
                return False

    # place bracket order (limit, take profit and stop loss)
    take_profit = round(price * (1 + PROFIT) if action ==
                        "BUY" else price * (1 - PROFIT), 2)
    stop_loss = round(price * (1 - RISK) if action ==
                      "BUY" else price * (1 + RISK), 2)

    bracket = ib.bracketOrder(action, quantity,
                              limitPrice=price,
                              takeProfitPrice=take_profit,
                              stopLossPrice=stop_loss)

    # set trades to expire if not filled within X seconds
    expiration = datetime.now() + timedelta(seconds=WAIT_FOR_FILL)
    bracket[0].goodTillDate = expiration.strftime("%Y%m%d %H:%M:%S")
    bracket[0].tif = "GTD"

    # place all separate orders
    trades = [ib.placeOrder(contract, order) for order in bracket]

    ib.sleep(1)
    return trades[0]


async def calculate_quantity(price, success):
    """Calculates quantity of trade based on kelly criterion 

    Args:
        price (Float): Price of contract
        success (Float): Probability of trade being successful

    Returns:
        Int: Quantity of shares to buy or sell
    """

    kelly_criterion = (success - (1 - success))
    amount = kelly_criterion * MAXIMUM_ORDER
    quantity = math.ceil(amount / price if amount > 2000 else 2001 / price)

    return quantity


async def run(contracts, points, settings):
    """The main algorithm function and trading bot

    Args:
        contracts ([Contract]): List of contracts to run algorithm on
        points (Dict<String, [Float]>): A dictionary with a list of points for each contract
        settings (Dict<String, Any>): A dictionary of settings found in the google spreadsheet
    """

    print("Starting to scan for: " +
          ", ".join([contract.symbol for contract in contracts]))

    # fill in missing fields for the contract
    ib.qualifyContracts(*contracts)

    # get candle history for all contracts
    history = get_history(contracts)

    # for each contract, subscribe to the live bar updates
    for contract in contracts:
        ib.reqRealTimeBars(contract, 5, "MIDPOINT", True)

    # for each bar that comes in every 5 seconds
    async for bars, _ in ib.barUpdateEvent:
        current_bar = bars[-1]
        print(current_bar)

        # if its a 30 second candles
        if current_bar.time.second % 30 == 0:

            # update the history with the new candle
            history[bars.contract.symbol].pop(0)
            history[bars.contract.symbol].append(current_bar.close)

            # calculate the pearson correlation coefficient
            r = pearson(history[bars.contract.symbol])

            # get all supports/resistances
            pivots = points[bars.contract.symbol]

            for pivot in pivots:
                # if support/resistance is within X%
                if pivot[0] * (1 - ALPHA) <= current_bar.close <= pivot[0] * (1 + ALPHA):

                    # if price going down and visible downward trend in past X seconds
                    if current_bar.close > pivot[0] * (1 - ALPHA) and r < -CORRELATION_STRENGTH:

                        print("Going down - " + bars.contract.symbol +
                              " - " + str(current_bar.close) + " - " + str(r))

                        # if trade meets minimum probability, execute
                        if pivot[1] > settings[bars.contract.symbol]["minimum_probability"]:
                            # calculate to trade with based on risk
                            quantity = calculate_quantity(pivot[0], pivot[1])

                            # place order
                            order = place_order(
                                "BUY", bars.contract, quantity, pivot[0])
                            if order:
                                print("Placed LONG for " + str(quantity) + " shares of " +
                                      bars.contract.symbol + " at $" + str(current_bar.close))

                    # if price going up and visible upward trend in past X seconds
                    if current_bar.close < pivot[0] * (1 + ALPHA) and r > CORRELATION_STRENGTH:

                        print("Going up - " + bars.contract.symbol +
                              " - " + str(current_bar.close) + " - " + str(r))

                        # if trade meets minimum probability, execute
                        if pivot[2] > settings[bars.contract.symbol]["minimum_probability"]:

                            # calculate to trade with based on risk
                            quantity = calculate_quantity(pivot[0], pivot[2])

                            # place order
                            order = place_order(
                                "SELL", bars.contract, quantity, pivot[0])
                            if order:
                                print("Placed SHORT for " + str(quantity) + " shares of " +
                                      bars.contract.symbol + " at $" + str(current_bar.close))

try:
    # load points and settings from google spreadsheets into dictionary
    points, settings = get_points_and_settings()

    # create a list of contracts to run algorithm on
    stocks = [symbol for symbol in settings.keys() if settings[symbol]["enabled"]]
    contracts = [Stock(pair,  "SMART", "USD") for pair in stocks]

    # run the algorithm
    asyncio.run(run(contracts, points, settings))
except (KeyboardInterrupt, SystemExit):
    ib.disconnect()
