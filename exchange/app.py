from decimal import Decimal, getcontext
from typing import Any

from exchange.db import ExchangeRate, User, UserCurrency, create_session
from exchange.exception import UserNotFound
from flask import Flask, jsonify, request

server = Flask(__name__)


@server.errorhandler(UserNotFound)
def handle_not_found_user(error: Any) -> Any:
    return jsonify({'ERROR': '{0}'.format(error)}), 404


def create_market():
    lst = ["btc", "eth", "xpr", "trx", "ltc"]
    price = 10
    with create_session() as session:
        for name in lst:
            currency: ExchangeRate = ExchangeRate(name, str(price), str(price + 2))
            session.add(currency)
            price += 10


@server.route('/market/api/v1.0/registration', methods=['POST'])
def registration() -> Any:
    if not request.json or 'name' not in request.json:
        return (
            jsonify({'ERROR': 'Invalid data, please give username'}),
            400,
        )
    name: str = request.json.get("name")
    with create_session() as session:
        user: User = User(request.json.get("name"))
        session.add(user)
        session.commit()
        portfolio: UserCurrency = UserCurrency(user.id)
        session.add(portfolio)
    return jsonify({"REGISTRATION": name})


@server.route('/market/api/v1.0/<identification>/get_ye', methods=['GET'])
def get_count_ye(identification: str) -> Any:
    with create_session() as session:
        user = session.query(User).filter(User.id == int(identification)).first()
        if user is not None:
            return jsonify({"COUNT_YE": user.ye})
        raise UserNotFound("User not found")


@server.route('/market/api/v1.0/<identification>/get_portfolio', methods=['GET'])
def get_portfolio(identification: str) -> Any:
    with create_session() as session:
        portfolio = (
            session.query(UserCurrency)
            .filter(UserCurrency.user_id == int(identification))
            .first()
        )
        if portfolio is not None:
            return jsonify(
                {
                    "PORTFOLIO": {
                        "btc": portfolio.btc,
                        "eth": portfolio.eth,
                        "xpr": portfolio.xpr,
                        "trx": portfolio.trx,
                        "ltc": portfolio.ltc,
                    }
                }
            )
        raise UserNotFound("User not found")


@server.route('/market/api/v1.0/get_exchange_rate_all', methods=['GET'])
def get_exchange_rate_all() -> Any:
    result: dict = {}
    with create_session() as session:
        for currency in session.query(ExchangeRate):
            result[currency.name] = "sold price : {0}, buy price : {1}".format(
                currency.sold_price, currency.buy_price
            )
    return jsonify({"EXCHANGE RATE": result})


def check_request(rq):
    if not rq.json or "name" not in rq.json or "count" not in rq.json:
        return jsonify({"ERROR": "Please write count and currency name"}), 404
    name_currency = rq.json.get("name")
    try:
        getcontext().prec = 5
        count = Decimal(rq.json.get("count"))
        assert count >= 0
    except (ValueError, AssertionError):
        return jsonify({"ERROR": "Count of currency must be a number above zero"}), 404
    return name_currency, count


def prepare_transaction(name_currency, count, identification):
    with create_session(expire_on_commit=False) as session:
        getcontext().prec = 5
        price_currency = (
            session.query(ExchangeRate)
            .filter(ExchangeRate.name == name_currency)
            .first()
            .sold_price
        )
        price_transaction = Decimal(price_currency) * Decimal(count)
        users_ye = Decimal(
            session.query(User).filter(User.id == int(identification)).first().ye
        )
        users_currency = (
            session.query(UserCurrency)
            .filter(UserCurrency.user_id == int(identification))
            .first()
        )
        if users_currency is None or users_ye is None:
            raise UserNotFound("User not found")
        return price_currency, price_transaction, users_ye, users_currency


def create_json(user_ye, name_currency, update_user_currency):
    return jsonify(
        {
            "DO TRANSACTION": {
                "YE NOW": "{}".format(user_ye),
                "{0} NOW".format(name_currency): "{0}".format(update_user_currency),
            }
        }
    )


@server.route('/market/api/v1.0/<identification>/buy', methods=['POST'])
def buy_currency(identification: str):
    name_currency, count_buy = check_request(request)
    sold_price, price_transaction, user_ye, user_currency = prepare_transaction(
        name_currency, count_buy, identification
    )

    with create_session() as session:
        getcontext().prec = 5
        if Decimal(user_ye) >= price_transaction:
            user_ye -= price_transaction
            session.query(User).filter(User.id == int(identification)).first().ye = str(
                user_ye
            )
            #           я не смог понять, как достать конкретное поле из записи по имени,
            #           по-этому через getattr и setattr
            #           наверное таблица UsersCurrency кривая и надо было сделать ее в две колонки
            #           и был бы один и тот же юзер много раз с разными валютами?
            update_user_currency = Decimal(
                getattr(user_currency, name_currency)
            ) + Decimal(count_buy)

            setattr(
                session.query(UserCurrency)
                .filter(UserCurrency.user_id == int(identification))
                .first(),
                name_currency,
                str(update_user_currency),
            )
            if user_ye is None:
                raise UserNotFound("User not found")
            return create_json(user_ye, name_currency, update_user_currency)
    return jsonify({"ERROR": "Not enough ye for this transaction"})


@server.route('/market/api/v1.0/<identification>/sold', methods=['POST'])
def sold_currency(identification: str):
    name_currency, count_sold = check_request(request)
    buy_price, price_transaction, user_ye, user_currency = prepare_transaction(
        name_currency, count_sold, identification
    )

    with create_session() as session:
        getcontext().prec = 5
        if Decimal(getattr(user_currency, name_currency)) >= count_sold:
            user_ye += price_transaction
            session.query(User).filter(User.id == int(identification)).first().ye = str(
                user_ye
            )
            update_user_currency = Decimal(
                getattr(user_currency, name_currency)
            ) - Decimal(count_sold)

            setattr(
                session.query(UserCurrency)
                .filter(UserCurrency.user_id == int(identification))
                .first(),
                name_currency,
                str(update_user_currency),
            )
            return create_json(user_ye, name_currency, update_user_currency)
    return jsonify({"ERROR": "Not enough currency for this transaction"})
