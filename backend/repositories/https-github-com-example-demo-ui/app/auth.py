def login(username, password):
    if username == 'admin' and password == 'secret':
        return 'ok'
    return 'denied'
