from nicegui import ui, app
from components.header import header
from components.footer import footer
from utils import api

@ui.page('/reports')
def reports():
    header()
    if not app.storage.user.get(str('token')):
        ui.navigate.to('/login')
        return
    r = api('/api/reports', 'GET', params={'page': 1, 'page_size': 8})
    if not r.ok:
        with ui.column().classes('items-center justify-center min-h-[60vh]'):
            ui.label(f'Failed to load reports: {r.status_code}').classes('text-red-700')
            ui.label(r.text[:400]).classes('text-red-500 text-sm')
            with ui.row().classes('mt-2'):
                ui.link('Upload a report', '/upload')
        footer()
        return
    try:
        data = r.json()
    except Exception:
        with ui.column().classes('items-center justify-center min-h-[60vh]'):
            ui.label('Server returned non-JSON for /api/reports').classes('text-red-700')
            ui.label(r.text[:400]).classes('text-red-500 text-sm')
        footer()
        return
    items = data if isinstance(data, list) else (data.get('items') or data.get('reports') or [])
    if not items:
        with ui.column().classes('items-center justify-center min-h-[80vh] w-full'):
            with ui.card().classes('rounded-2xl shadow-lg bg-white p-8 flex flex-col items-center w-full'):
                ui.icon('insert_drive_file').classes('text-6xl text-slate-400 mb-4')
                ui.label('No reports found').classes('text-3xl font-bold mb-1 font-sans text-slate-800')
                ui.label('You have not uploaded any lab reports yet.').classes('text-base text-slate-700 mb-4 font-sans')
                ui.button('Upload your first report', on_click=lambda: ui.navigate.to('/upload'))\
                    .classes('mt-2 rounded-full px-6 py-2 text-lg font-semibold shadow')\
                    .style('background-color:#fff !important;color:#059669 !important;border:2px solid #059669 !important;')
        footer()
        return
    with ui.column().classes('max-w-4xl mx-auto w-full gap-6 py-10'):
        ui.label('Your Lab Reports').classes('text-3xl font-bold mb-1 font-sans text-left')
        ui.label('View, open, or delete your uploaded lab reports.').classes('text-base text-slate-600 mb-6 font-sans text-left')
        search_val = {'value': ''}
        sex_val = {'value': 'All'}
        age_val = {'value': ''}
        filtered = {'value': items[:]}
        def delete_report(report_id):
            dialog = ui.dialog()
            with dialog:
                with ui.card().classes('p-4'):
                    ui.label('Delete Report').classes('text-lg font-bold mb-2 text-red-700')
                    ui.label('Are you sure you want to delete this report? This cannot be undone.').classes('mb-4')
                    def do_delete():
                        r = api(f'/api/report/{report_id}', 'DELETE')
                        if r.ok:
                            ui.notify('Report deleted', type='success')
                            nonlocal items
                            items = [item for item in items if (item.get('id') or item.get('report_id')) != report_id]
                            filtered['value'] = [item for item in filtered['value'] if (item.get('id') or item.get('report_id')) != report_id]
                            dialog.close()
                            render_reports()
                        else:
                            ui.notify('Failed to delete report', type='warning')
                            dialog.close()
                    ui.button('Delete', on_click=do_delete).style('background-color:#dc2626 !important;color:#fff !important;').classes('rounded-full px-4 py-1 font-semibold')
                    ui.button('Go to Reports', on_click=lambda: ui.navigate.to('/reports')).classes('rounded-full px-6 py-2 text-lg font-semibold shadow w-full sm:w-auto').style('background-color:#059669 !important;color:#fff !important;border:none !important;')
            dialog.open()
        def do_search():
            q = search_val['value'].strip().lower()
            def match(it):
                if q:
                    if not (q in str(it.get('report_name', '')).lower() or q in str(it.get('name', '')).lower()):
                        return False
                return True
            filtered['value'] = [it for it in items if match(it)]
            render_reports()
        def do_filter():
            s = sex_val['value'] or 'All'
            a = age_val['value'].strip()
            def match(it):
                if s != 'All' and (it.get('sex', '').capitalize() != s):
                    return False
                if a:
                    try:
                        if str(it.get('age', '')).strip() != str(a):
                            return False
                    except Exception:
                        return False
                return True
            filtered['value'] = [it for it in items if match(it)]
            render_reports()
        with ui.row().classes('items-end gap-4 flex-nowrap').style('border:1px solid #05966933;border-radius:10px;padding:18px 16px 12px 16px;margin-bottom:18px;background:#fff;'):
            ui.input('Search by name...').bind_value(search_val, 'value').classes('w-full sm:w-64 mb-2 sm:mb-0').style('display:inline-flex;vertical-align:bottom;')
            ui.button('Search', on_click=do_search).classes('rounded-full px-4 py-1 font-semibold w-full sm:w-auto').style('background-color:#059669 !important;color:#fff !important;border:none !important;display:inline-flex;vertical-align:bottom;')
            ui.html('<div class="hidden sm:block" style="width:1px;height:32px;background:#05966922;margin:0 18px;"></div>')
            ui.select(['All', 'Male', 'Female'], label='Sex').bind_value(sex_val, 'value').classes('w-full sm:w-32 mb-2 sm:mb-0').style('display:inline-flex;vertical-align:bottom;')
            ui.input('Age').bind_value(age_val, 'value').classes('w-full sm:w-24 mb-2 sm:mb-0').style('display:inline-flex;vertical-align:bottom;')
            ui.button('Apply', on_click=do_filter).classes('rounded-full px-4 py-1 font-semibold w-full sm:w-auto').style('background-color:#059669 !important;color:#fff !important;border:none !important;display:inline-flex;vertical-align:bottom;')
        report_grid = ui.column().classes('w-full')
        def render_reports():
            report_grid.clear()
            if not filtered['value']:
                with report_grid:
                    with ui.column().classes('items-center justify-center min-h-[40vh] w-full'):
                        ui.icon('insert_drive_file').classes('text-6xl text-slate-400 mb-4')
                        ui.label('No reports found').classes('text-3xl font-bold mb-1 font-sans text-slate-800')
                        ui.label('No reports match your search or filter.').classes('text-base text-slate-700 mb-4 font-sans')
            with report_grid:
                with ui.row().classes('w-full gap-6 flex-wrap items-stretch'):
                    for it in filtered['value']:
                        col_classes = 'flex-1 min-w-[280px] max-w-[420px] mb-4 flex flex-col'
                        with ui.element('div').classes(col_classes):
                                rid = it.get('id') or it.get('report_id')
                                report_name = it.get('report_name') or it.get('name') or 'Lab Report'
                                age = it.get('age') or ''
                                sex = it.get('sex') or ''
                                status = it.get('status') or 'done'
                                uploaded = it.get('uploaded_at') or it.get('created_at') or ''
                                with ui.card().classes('rounded-2xl shadow bg-white p-6 flex flex-col md:flex-row items-center justify-between gap-4 hover:shadow-lg transition-shadow h-full'):
                                    with ui.column().classes('flex-1 gap-1'):
                                        ui.label(report_name).classes('font-semibold text-lg text-emerald-800')
                                        if age or sex:
                                            html_lines = []
                                            if age:
                                                html_lines.append(f'<span class="text-slate-600 text-sm"><b>Age:</b> {age}</span>')
                                            if sex:
                                                html_lines.append(f'<span class="text-slate-600 text-sm"><b>Sex:</b> {sex}</span>')
                                            ui.html('<br>'.join(html_lines))
                                        ui.label(f"Status: {status.capitalize()}").classes('text-slate-500 text-sm')
                                        if uploaded:
                                            ui.label(f"Uploaded: {uploaded}").classes('text-slate-400 text-xs')
                                    with ui.row().classes('gap-3'):
                                        if rid is not None:
                                            ui.button('OPEN', on_click=lambda r=rid: ui.navigate.to(f'/report/{r}')).classes('rounded-full px-5 py-1 font-semibold w-full sm:w-auto').style('background-color:#059669 !important;color:#fff !important;border:none !important;')
                                            ui.button('DELETE', on_click=lambda r=rid: delete_report(r)).classes('rounded-full px-5 py-1 font-semibold w-full sm:w-auto').style('background-color:#dc2626 !important;color:#fff !important;border:none !important;')
        render_reports()
    footer()
