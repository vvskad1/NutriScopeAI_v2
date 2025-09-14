from nicegui import ui, app
from components.header import header
from components.footer import footer
from utils import api

@ui.page('/upload')
def upload():
    header()
    if not app.storage.user.get(str('token')):
        ui.navigate.to('/signin')
        return
    with ui.element('div').classes('flex flex-row w-full min-h-[80vh]'):
        # Left: Upload form
        with ui.element('div').classes('flex-1 flex flex-col px-8 py-12 border-r border-emerald-200 bg-white overflow-hidden'):
            with ui.element('div').classes('w-full max-w-xl'):
                ui.label('Upload a Lab Report').classes('text-3xl font-bold mb-1 font-sans')
                ui.label('Get instant analysis and meal plan suggestions').classes('text-base text-slate-600 mb-4 font-sans')
                report_name = ui.input('Report name*').classes('w-full mb-2')
                age         = ui.input('Age*').classes('w-full mb-2')
                sex         = ui.select(['Male', 'Female'], label='Gender*').classes('w-full mb-4')
                file_bytes = {'data': None}
                file_name  = {'name': None}
                def on_pick(e):
                    file_bytes['data'] = e.content   # bytes
                    file_name['name']  = e.name
                    ui.notify(f'Selected: {e.name}')
                with ui.element('div').classes('flex flex-row justify-start w-full mb-4 items-center'):
                    ui.upload(
                        on_upload=on_pick,
                        auto_upload=True
                    ).props('accept=.pdf') \
                     .classes('hidden') \
                     .bind_visibility(lambda: False)  # Hide the default input
                    def trigger_upload():
                        ui.run_javascript("document.querySelector('input[type=file]').click()")
                    ui.button('Choose PDF', on_click=trigger_upload).classes('rounded-full px-6 py-2 text-lg font-semibold shadow').style('background-color:#fff !important;color:#059669 !important;border:2px solid #059669 !important;')
                    if file_name['name']:
                        ui.label(f"Selected: {file_name['name']}").classes('text-sm text-emerald-700 ml-4')
                def submit():
                    if not (file_bytes['data'] and file_name['name']):
                        ui.notify('Choose a PDF file', type='warning'); return
                    if not report_name.value or not age.value or not sex.value:
                        ui.notify('Fill report name, age, and sex', type='warning'); return
                    files = {'file': (file_name['name'], file_bytes['data'], 'application/pdf')}
                    data  = {'report_name': report_name.value, 'age': age.value, 'sex': sex.value}
                    r = api('/api/analyze', 'POST', files=files, data=data)
                    if r.ok:
                        j = r.json()
                        rid = (j.get('context') or {}).get('report_id')
                        ui.notify('Analyzed successfully')
                        if rid:
                            ui.navigate.to(f'/report/{rid}')
                    else:
                        ui.notify(r.text, type='warning')
                with ui.element('div').classes('flex flex-col items-start mt-4 max-w-sm w-full'):
                    ui.button('Upload & Analyze', on_click=submit).classes('w-full rounded-full py-3 text-base font-semibold shadow').style('background-color:#059669 !important;color:#fff !important;border:none !important;')
        # Right: Instructions
        with ui.element('div').classes('flex-1 flex flex-col bg-emerald-50 px-8 py-12 items-center justify-center'):
            ui.label('How to Upload a Lab Report').classes('text-2xl font-bold mb-4 text-emerald-800')
            ui.markdown('''
1. Click **Choose PDF** and select your lab report file (PDF only).
2. Enter a name for your report, your age, and select your gender.
3. Click **Upload & Analyze** to process your report.
4. After successful upload, you will be redirected to your report page.
5. You can view all your reports anytime on the [Reports](/reports) page.
            ''').classes('text-base text-slate-700 mb-6')
            ui.label('Tips:').classes('text-lg font-semibold mb-2 text-emerald-700')
            ui.markdown('''
- Make sure your PDF is clear and contains lab results.
- If upload fails, check your internet connection and file format.
- For privacy, all processing is done securely.
            ''').classes('text-base text-slate-700 mb-4')
            ui.button('Go to Reports', on_click=lambda: ui.navigate.to('/reports')).classes('rounded-full px-6 py-2 text-lg font-semibold shadow').style('background-color:#059669 !important;color:#fff !important;border:none !important;')
    footer()
