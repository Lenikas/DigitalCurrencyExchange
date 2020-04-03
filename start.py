from exchange.app import server, change_exchange_rate, create_market
from exchange.db import ExchangeRate, create_session, Decimal
from threading import Thread


def start():
    server.run()


if __name__ == '__main__':
    create_market()
    th1 = Thread(target=start)
    th2 = Thread(target=change_exchange_rate)
    th1.start()
    th2.start()

