import os
import requests
from nicegui import app, ui

API_BASE = os.getenv('API_BASE', 'http://127.0.0.1:8000')

def api(path, method='GET', **kw):
    headers = kw.pop('headers', {})
    token = app.storage.user.get(str('token'))
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return requests.request(method, f'{API_BASE}{path}', headers=headers, **kw)

def set_user(token: str | None, user: dict | None):
    def stringify_keys(obj):
        if isinstance(obj, dict):
            return {str(k): stringify_keys(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [stringify_keys(i) for i in obj]
        else:
            return obj
    if token and user:
        app.storage.user[str('token')] = token
        safe_user = stringify_keys(user)
        app.storage.user[str('user')] = safe_user
    else:
        app.storage.user.pop(str('token'), None)
        app.storage.user.pop(str('user'), None)

def signout():
    set_user(None, None)
    ui.notify('Signed out')
    ui.navigate.to('/signin')
