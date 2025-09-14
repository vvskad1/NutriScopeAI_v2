from nicegui import ui, app
from components.header import header
from components.footer import footer
from utils import api, set_user

@ui.page('/signin')
def signin():
    header()
    with ui.column().classes('items-center justify-center min-h-[80vh] w-full'):
        with ui.column().classes('items-center justify-center w-full max-w-2xl mx-auto text-center'):
            ui.label('Sign in to your account').classes('text-3xl font-bold mb-1 font-sans')
            ui.label('Access your lab reports and personalized meal plans').classes('text-base text-slate-600 mb-4 font-sans')
            email = ui.input('Email*').classes('w-full mb-2')
            pw = ui.input('Password*', password=True, password_toggle_button=True).classes('w-full mb-4')
            def go():
                r = api('/api/auth/login', 'POST', json={'email': email.value, 'password': pw.value})
                if r.ok:
                    j = r.json()
                    set_user(j.get('token'), j.get('user'))
                    ui.notify('Signed in!')
                    ui.navigate.to('/')
                else:
                    ui.notify(r.text, type='warning')
            ui.button('Sign In', on_click=go).classes('w-full rounded-full py-3 text-base mt-2 font-semibold shadow').style('background-color:#059669 !important;color:#fff !important;border:none !important;')
            ui.markdown('Don\'t have an account? [Sign up](/signup)').classes('mt-3 text-center text-sm')
    footer()

@ui.page('/login')
def login():
    return signin()
