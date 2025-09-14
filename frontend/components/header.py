from nicegui import ui, app
from utils import signout

def header():
    with ui.row().classes('w-full items-center justify-between px-8 py-3 bg-white shadow-sm font-sans'):
        # Logo left
        with ui.row().classes('items-center gap-2'):
            ui.label('NutriScope AI').classes('text-2xl font-bold text-emerald-700')
        # Nav links centered (no underline)
        with ui.row().classes('gap-8 flex-1 justify-center'):
            ui.link('HOME', '/').classes('text-base font-medium text-gray-700 hover:text-emerald-700 no-underline')
            ui.link('UPLOAD', '/upload').classes('text-base font-medium text-gray-700 hover:text-emerald-700 no-underline')
            ui.link('REPORTS', '/reports').classes('text-base font-medium text-gray-700 hover:text-emerald-700 no-underline')
            ui.link('ABOUT', '/about').classes('text-base font-medium text-gray-700 hover:text-emerald-700 no-underline')
        # User info and sign out right
        with ui.row().classes('gap-4 items-center'):
            user = app.storage.user.get(str('user'))
            if user:
                ui.label(user.get('name', '')).classes('text-base text-gray-700')
                ui.button('SIGN OUT', on_click=signout).classes('rounded-full px-4 py-1 font-semibold').style('background-color:#059669 !important;color:#fff !important;border:none !important;')
            else:
                ui.button('SIGN IN', on_click=lambda: ui.navigate.to('/signin')).classes('rounded-full px-4 py-1 font-semibold').style('background-color:#059669 !important;color:#fff !important;border:none !important;')
                ui.button('SIGN UP', on_click=lambda: ui.navigate.to('/signup')).classes('rounded-full px-4 py-1 font-semibold').style('background-color:#059669 !important;color:#fff !important;border:none !important;')
