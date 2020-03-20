from exchange.app import server, create_market


if __name__ == '__main__':
    create_market()
    server.run(debug=True)
