from contextlib import contextmanager
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = sa.create_engine('sqlite:///test.sqlite')
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
    btc = sa.Column(sa.String)
    eth = sa.Column(sa.String)
    xpr = sa.Column(sa.String)
    trx = sa.Column(sa.String)
    ltc = sa.Column(sa.String)

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.btc = str(0)
        self.eth = str(0)
        self.xpr = str(0)
        self.trx = str(0)
        self.ltc = str(0)


class ExchangeRate(Base):
    __tablename__ = "exchange_rate"

    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    name = sa.Column(sa.String)
    sold_price = sa.Column(sa.String)
    buy_price = sa.Column(sa.String)

    def __init__(self, name: str, sold_price: str, buy_price: str):
        self.name = name
        self.sold_price = sold_price
        self.buy_price = buy_price


Base.metadata.create_all(engine)
