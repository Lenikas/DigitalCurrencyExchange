from contextlib import contextmanager
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = sa.create_engine('sqlite:///bd.sqlite')
Session = sessionmaker(bind=engine)
Base: Any = declarative_base()


@contextmanager
def create_session(**kwargs: Any) -> Any:
    new_session = Session(**kwargs)
    try:
        yield new_session
        new_session.commit()
    except Exception:
        new_session.rollback()
        raise
    finally:
        new_session.close()


class User(Base):
    __tablename__ = 'user'

    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    name = sa.Column(sa.String(100), nullable=False)
    ye = sa.Column(sa.String)

    def __init__(self, name: str):
        self.name = name
        self.ye = str(Decimal(1000))


class UserCurrency(Base):
    __tablename__ = 'user_currency'

    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    user_id = sa.Column(sa.Integer, sa.ForeignKey(User.id), nullable=False)
    name_currency = sa.Column(sa.String)
    count_currency = sa.Column(sa.String)

    def __init__(self, user_id: int, name: str):
        self.user_id = user_id
        self.name_currency = name
        self.count_currency = str(0)


class ExchangeRate(Base):
    __tablename__ = 'exchange_rate'

    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    name = sa.Column(sa.String, unique=True)
    sold_price = sa.Column(sa.String)
    buy_price = sa.Column(sa.String)

    def __init__(self, name: str, sold_price: Decimal, buy_price: Decimal):
        self.name = name
        self.sold_price = str(sold_price)
        self.buy_price = str(buy_price)


class UserOperations(Base):
    __tablename__ = 'user_operations'

    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    user_id = sa.Column(sa.Integer, sa.ForeignKey(User.id), nullable=False)
    action = sa.Column(sa.String)
    currency = sa.Column(sa.String)
    count = sa.Column(sa.String)
    #    price_transaction = sa.Column(sa.String)

    def __init__(self, user_id: int, action: str, currency: str, count: Decimal):
        #   тут линт ругается,что больше 5 аргументов, я уберу один,
        #   просто по записи будет неясно, что сделал пользователь
        self.user_id = user_id
        self.action = action
        self.currency = currency
        self.count = str(count)

    #   self.price_transaction = str(price)


Base.metadata.create_all(engine)
