from nicegui import ui

def footer():
    with ui.row().classes('w-full justify-between items-center px-8 py-4 bg-white shadow-sm font-sans').style('position:sticky;bottom:0;z-index:50;'):
        ui.label('Developed by Venkata Sai Krishna Aditya Vatturi').classes('text-xs text-slate-500')
        with ui.row().classes('gap-4 items-center'):
            ui.link('LinkedIn', 'https://www.linkedin.com/in/vvs-krishna-aditya-2002vvsk/', new_tab=True).classes('no-underline text-emerald-700 hover:underline')
            ui.link('GitHub', 'https://github.com/vvskad1', new_tab=True).classes('no-underline text-emerald-700 hover:underline')
            ui.link('Devpost', 'https://devpost.com/vvatturi', new_tab=True).classes('no-underline text-emerald-700 hover:underline')
