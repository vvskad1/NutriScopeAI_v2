from nicegui import ui, app
from components.header import header
from components.footer import footer
from utils import api

@ui.page('/signup')
def signup():
    header()
    with ui.column().classes('items-center justify-center min-h-[80vh] w-full'):
        with ui.column().classes('items-center justify-center w-full max-w-2xl mx-auto text-center'):
            ui.label('Create your account').classes('text-3xl font-bold mb-1 font-sans')
            ui.label('Upload and summarize lab reports securely').classes('text-base text-slate-600 mb-4 font-sans')
            name = ui.input('Full name*').classes('w-full mb-2')
            email = ui.input('Email*').classes('w-full mb-2')
            pw = ui.input('Password*', password=True, password_toggle_button=True).classes('w-full mb-4')
            ui.label('Minimum 8 characters is recommended.').classes('text-xs text-slate-400 mb-2')
            def go():
                r = api('/api/auth/signup', 'POST', json={'name': name.value, 'email': email.value, 'password': pw.value})
                if r.ok:
                    app.storage.user[str('signup_name')] = name.value  # Store name for greeting
                    ui.notify('Account created!')
                    ui.navigate.to('/signin')
                else:
                    ui.notify(r.text, type='warning')
            ui.button('Create account', on_click=go).classes('w-full rounded-full py-3 text-base mt-2 font-semibold shadow').style('background-color:#059669 !important;color:#fff !important;border:none !important;')
            ui.markdown('Already have an account? [Sign in](/signin)').classes('mt-3 text-center text-sm')
    footer()
