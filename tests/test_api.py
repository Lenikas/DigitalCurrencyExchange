import json
from decimal import Decimal

import pytest
from exchange.app import create_market, server
from exchange.db import Base, UserCurrency, create_session, engine


@pytest.fixture(autouse=True)
def _init_db():
    Base.metadata.create_all(engine)
    create_market()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client():
    with server.test_client() as client:
        yield client


def registration(client):
    return client.post(
        '/market/api/v1.0/registration',
        data=json.dumps({'name': 'username'}),
        content_type='application/json',
    )


def buy_currency(client):
    return client.post(
        '/market/api/v1.0/1/buy',
        data=json.dumps({'name': 'btc', 'count': '10'}),
        content_type='application/json',
    )


def test_registration_bad_request(client):
    response = client.post(
        '/market/api/v1.0/registration',
        data=json.dumps({'not name': 'username'}),
        content_type='application/json',
    )
    data = json.loads(response.get_data())
    assert response.status_code == 400
    assert data['ERROR'] == 'Invalid data, please give username'


def test_registration_success(client):
    response = registration(client)
    data = json.loads(response.get_data())
    assert response.status_code == 200
    assert data['REGISTRATION'] == 'username'


def test_registration_portfolio(client):
    registration(client)
    with create_session() as session:
        portfolio = session.query(UserCurrency).all()
        for item in portfolio:
            assert item.count_currency == '0'


@pytest.mark.parametrize('url', ('get_ye', 'get_portfolio', 'get_operations'))
def test_get_count_ye_portfolio_operations_empty(client, url):
    response = client.get('/market/api/v1.0/1/{0}'.format(url))
    assert response.status_code == 404
    assert json.loads(response.get_data())['ERROR'] == 'User not found'


def test_get_count_ye(client):
    registration(client)
    data = client.get('/market/api/v1.0/1/get_ye')
    assert json.loads(data.get_data())['COUNT_YE'] == '1000'


def test_get_portfolio(client):
    registration(client)
    response = client.get('/market/api/v1.0/1/get_portfolio')
    data = json.loads(response.get_data())
    assert isinstance(data['PORTFOLIO'], dict)
    assert len(data['PORTFOLIO']) == 5
    assert data['PORTFOLIO']['btc'] == '0'


def test_get_exchange_rate(client):
    response = client.get('/market/api/v1.0/get_exchange_rate_all')
    data = json.loads(response.get_data())
    assert isinstance(data['EXCHANGE RATE'], dict)
    assert len(data['EXCHANGE RATE']) == 5
    assert data['EXCHANGE RATE']['btc'] != '0'


def test_check_request_bad_name(client):
    registration(client)
    response = client.post(
        '/market/api/v1.0/1/buy',
        data=json.dumps({'bad_name': 'btc', 'count': '1'}),
        content_type='application/json',
    )
    data = json.loads(response.get_data())
    assert (
        data['ERROR'] == 'Please write count and currency name, count must be more zero'
    )


def test_check_request_bad_count(client):
    registration(client)
    response = client.post(
        '/market/api/v1.0/1/buy',
        data=json.dumps({'name': 'btc', 'count': '-1'}),
        content_type='application/json',
    )
    data = json.loads(response.get_data())
    assert (
        data['ERROR'] == 'Please write count and currency name, count must be more zero'
    )


def test_buy_success(client):
    registration(client)
    response = client.post(
        '/market/api/v1.0/1/buy',
        data=json.dumps({'name': 'btc', 'count': '10'}),
        content_type='application/json',
    )
    data = json.loads(response.get_data())
    assert isinstance(data['DO TRANSACTION'], dict)
    assert Decimal(data['DO TRANSACTION']['YE NOW']) < Decimal('1000')
    assert Decimal(data['DO TRANSACTION']['btc NOW']) == Decimal(10)


@pytest.mark.parametrize('url', ('buy', 'sold'))
def test_buy_sold_failed(client, url):
    registration(client)
    response = client.post(
        '/market/api/v1.0/1/{0}'.format(url),
        data=json.dumps({'name': 'btc', 'count': '100000'}),
        content_type='application/json',
    )
    data = json.loads(response.get_data())
    if url == 'buy':
        assert data['ERROR'] == 'Not enough ye for this transaction'
    else:
        assert data['ERROR'] == 'Not enough currency for this transaction'


@pytest.mark.parametrize('url', ('buy', 'sold'))
def test_buy_sold_user_not_exist(client, url):
    response = client.post(
        '/market/api/v1.0/1/{0}'.format(url),
        data=json.dumps({'name': 'btc', 'count': '10'}),
        content_type='application/json',
    )
    data = json.loads(response.get_data())
    assert data['ERROR'] == 'User not found'


def test_sold_success(client):
    registration(client)
    buy_currency(client)
    response = client.post(
        '/market/api/v1.0/1/sold',
        data=json.dumps({'name': 'btc', 'count': '10'}),
        content_type='application/json',
    )
    data = json.loads(response.get_data())
    assert isinstance(data['DO TRANSACTION'], dict)
    assert Decimal(data['DO TRANSACTION']['YE NOW']) > Decimal('900')
    assert Decimal(data['DO TRANSACTION']['btc NOW']) == Decimal(0)


def test_add_currency_bad_request(client):
    response = client.post(
        '/market/api/v1.0/add',
        data=json.dumps({'name': 'btc'}),
        content_type='application/json',
    )
    data = json.loads(response.get_data())
    assert response.status_code == 404
    assert data['ERROR'] == 'Please write currency name, sold price and buy price'


def test_add_currency_bad_price(client):
    response = client.post(
        '/market/api/v1.0/add',
        data=json.dumps({'name': 'new', 'sold_price': -1, 'buy_price': -1}),
        content_type='application/json',
    )
    data = json.loads(response.get_data())
    assert response.status_code == 404
    assert data['ERROR'] == 'Sold price and buy price must be above zero'


def test_add_currency_success(client):
    response = client.post(
        '/market/api/v1.0/add',
        data=json.dumps({'name': 'new', 'sold_price': 1, 'buy_price': 1}),
        content_type='application/json',
    )
    data = json.loads(response.get_data())
    assert data['ADD CURRENCY']['name'] == 'new'
    assert data['ADD CURRENCY']['sold_price'] == '1'
    assert data['ADD CURRENCY']['buy_price'] == '1'


def test_get_operations(client):
    registration(client)
    buy_currency(client)
    response = client.get('/market/api/v1.0/1/get_operations')
    data = json.loads(response.get_data())
    assert len(data['OPERATIONS']) == 1
    assert data['OPERATIONS']['0'] == 'action: buy, currency: btc, count: 10'
