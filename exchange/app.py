import time
from datetime import datetime
from decimal import Decimal, getcontext
from random import uniform
from typing import Any, List, Tuple, Dict

from exchange.db import ExchangeRate, User, UserCurrency, UserOperations, create_session
from exchange.exception import CurrencyNotFound, UserNotFound
from flask import Flask, jsonify, request

server = Flask(__name__)


@server.errorhandler(UserNotFound)
def handle_not_found_user(error: str) -> Any:
    return jsonify({'ERROR': '{0}'.format(error)}), 404


@server.errorhandler(CurrencyNotFound)
def handle_not_found_currency(error: str) -> Any:
    return jsonify({'ERROR': '{0}'.format(error)}), 404


def create_market():
    lst = ['btc', 'eth', 'xpr', 'trx', 'ltc']
    price = 10
    with create_session() as session:
        for name in lst:
            session.add(ExchangeRate(name, Decimal(price + 2), Decimal(price)))
            price += 10


def create_portfolio(id_user: int, all_currencies: Any) -> List[UserCurrency]:
    portfolios = []
    for item in all_currencies:
        portfolios.append(UserCurrency(id_user, item.name))
    return portfolios


def change_exchange_rate() -> None:
    while True:
        time.sleep(10)
        with create_session() as session:
            percent = Decimal(uniform(0.9, 1.1))
            for currency in session.query(ExchangeRate):
                getcontext().prec = 5
                currency.sold_price = str(Decimal(currency.sold_price) * percent)
                currency.buy_price = str(Decimal(currency.buy_price) * percent)


def check_time(time_now: datetime) -> datetime:
    if datetime.now().second > time_now.second + 9:
        time_now = datetime.now()
        return jsonify({'ATTENTION': 'Exchange rate was changed!'})
    return time_now


@server.route('/market/api/v1.0/registration', methods=['POST'])
def registration() -> Any:
    if not request.json or 'name' not in request.json:
        return (
            jsonify({'ERROR': 'Invalid data, please give username'}),
            400,
        )
    name: str = request.json.get('name')

    with create_session() as session:
        user: User = User(request.json.get('name'))
        session.add(user)
        session.commit()
        all_currencies = session.query(ExchangeRate).all()
        portfolios = create_portfolio(user.id, all_currencies)
        for item in portfolios:
            session.add(item)
    return jsonify({'REGISTRATION': name})


@server.route('/market/api/v1.0/<identification>/get_ye', methods=['GET'])
def get_count_ye(identification: str) -> Any:
    with create_session() as session:
        user = session.query(User).filter(User.id == int(identification)).first()
        if user is not None:
            return jsonify({'COUNT_YE': user.ye})
        raise UserNotFound('User not found')


@server.route('/market/api/v1.0/<identification>/get_portfolio', methods=['GET'])
def get_portfolio(identification: str) -> Any:
    with create_session() as session:
        portfolio = (
            session.query(UserCurrency)
            .filter(UserCurrency.user_id == int(identification))
            .all()
        )
        if len(portfolio) != 0:
            result = {}
            for item in portfolio:
                result[item.name_currency] = item.count_currency
            return jsonify({'PORTFOLIO': result})
        raise UserNotFound('User not found')


@server.route('/market/api/v1.0/<identification>/get_operations', methods=['GET'])
def get_operations(identification: str) -> Any:
    with create_session() as session:
        operations = (
            session.query(UserOperations)
            .filter(UserOperations.user_id == int(identification))
            .all()
        )
        if len(operations) == 0:
            raise UserNotFound('User not found')
        result = {}
        for number, item in enumerate(operations):
            result[str(number)] = 'action: {0}, currency: {1}, count: {2}'.format(
                item.action, item.currency, item.count
            )
        return jsonify({'OPERATIONS': result})


@server.route('/market/api/v1.0/get_exchange_rate_all', methods=['GET'])
def get_exchange_rate_all() -> Any:
    result: Dict[str, str] = {}
    with create_session() as session:
        for currency in session.query(ExchangeRate):
            result[currency.name] = 'sold price : {0}, buy price : {1}'.format(
                currency.sold_price, currency.buy_price
            )
    return jsonify({'EXCHANGE RATE': result})


def check_request(rq: Any) -> Any:
    if not rq.json or 'name' not in rq.json or 'count' not in rq.json:
        return None, None
    name_currency = rq.json.get('name')
    try:
        getcontext().prec = 5
        count = rq.json.get('count')
        if Decimal(count) < 0:
            raise ValueError
    except ValueError:
        return None, None
    return name_currency, count


def prepare_transaction(
    name_currency: str, count: str, identification: str, action: str
) -> Tuple[Decimal, Decimal, Decimal]:
    with create_session(expire_on_commit=False) as session:
        getcontext().prec = 5
        price_currency = (
            session.query(ExchangeRate)
            .filter(ExchangeRate.name == name_currency)
            .first()
        )
        if price_currency is None:
            raise CurrencyNotFound('This currency does not exist')
        if action == 'buy':
            price_currency = price_currency.sold_price
        else:
            price_currency = price_currency.buy_price
        price_transaction = Decimal(price_currency) * Decimal(count)
        user_ye = session.query(User).filter(User.id == int(identification)).first()

        user_currency = (
            session.query(UserCurrency)
            .filter(UserCurrency.user_id == int(identification))
            .filter(UserCurrency.name_currency == name_currency)
            .first()
        )
        if user_currency is None or user_ye is None:
            raise UserNotFound('User not found')
        return (
            price_transaction,
            Decimal(user_ye.ye),
            Decimal(user_currency.count_currency),
        )


def create_json(user_ye: str, name_currency: str, update_user_currency: str) -> Any:
    return jsonify(
        {
            'DO TRANSACTION': {
                'YE NOW': '{}'.format(user_ye),
                '{0} NOW'.format(name_currency): '{0}'.format(update_user_currency),
            }
        }
    )


@server.route('/market/api/v1.0/<identification>/buy', methods=['POST'])
def buy_currency(identification: str) -> Any:
    name_currency, count_buy = check_request(request)
    if name_currency is None and count_buy is None:
        return (
            jsonify(
                {
                    'ERROR': 'Please write count and currency name, count must be more zero'
                }
            ),
            404,
        )

    price_transaction, user_ye, user_currency = prepare_transaction(
        name_currency, count_buy, identification, 'buy'
    )
    with create_session() as session:
        getcontext().prec = 5
        # check_time(TIME)
        if user_ye >= price_transaction:
            user_ye -= price_transaction
            session.query(User).filter(User.id == int(identification)).first().ye = str(
                user_ye
            )
            update_user_currency = user_currency + Decimal(count_buy)
            session.query(UserCurrency).filter(
                UserCurrency.user_id == int(identification)
            ).filter(
                UserCurrency.name_currency == name_currency
            ).first().count_currency = str(
                update_user_currency
            )
            session.add(
                UserOperations(int(identification), 'buy', name_currency, count_buy,)
            )
            return create_json(str(user_ye), name_currency, str(update_user_currency))
        return jsonify({'ERROR': 'Not enough ye for this transaction'})


@server.route('/market/api/v1.0/<identification>/sold', methods=['POST'])
def sold_currency(identification: str) -> Any:
    name_currency, count_sold = check_request(request)
    price_transaction, user_ye, user_currency = prepare_transaction(
        name_currency, count_sold, identification, 'sold'
    )

    with create_session() as session:
        getcontext().prec = 5
        # check_time(TIME)
        if user_currency >= Decimal(count_sold):
            user_ye += price_transaction
            session.query(User).filter(User.id == int(identification)).first().ye = str(
                user_ye
            )
            update_user_currency = user_currency - Decimal(count_sold)

            session.query(UserCurrency).filter(
                UserCurrency.user_id == int(identification)
            ).filter(
                UserCurrency.name_currency == name_currency
            ).first().count_currency = str(
                update_user_currency
            )
            session.add(
                UserOperations(int(identification), 'sold', name_currency, count_sold,)
            )
            return create_json(str(user_ye), name_currency, str(update_user_currency))
    return jsonify({'ERROR': 'Not enough currency for this transaction'})


@server.route('/market/api/v1.0/add', methods=['POST'])
def add_currency() -> Any:
    # изменить портфель валют
    if (
        not request.json
        or 'name' not in request.json
        or 'sold_price' not in request.json
        or 'buy_price' not in request.json
    ):
        return (
            jsonify({'ERROR': 'Please write currency name, sold price and buy price'}),
            404,
        )
    name_currency = request.json.get('name')
    try:
        getcontext().prec = 5
        sold_price = Decimal(request.json.get('sold_price'))
        buy_price = Decimal(request.json.get('buy_price'))
        if sold_price < 0 or buy_price < 0:
            raise ValueError
    except ValueError:
        return jsonify({'ERROR': 'Sold price and buy price must be above zero'}), 404

    with create_session() as session:
        session.add(ExchangeRate(name_currency, sold_price, buy_price))
        all_users = session.query(User).all()
        for user in all_users:
            session.add(UserCurrency(user.id, name_currency))

    return jsonify(
        {
            'ADD CURRENCY': {
                'name': name_currency,
                'sold_price': str(sold_price),
                'buy_price': str(buy_price),
            }
        }
    )
