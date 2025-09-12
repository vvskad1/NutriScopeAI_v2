from nicegui import ui, app
import requests, os

API_BASE = os.getenv('API_BASE', 'http://127.0.0.1:8000')

# ---------- API helper (adds Authorization header if logged in) ----------
def api(path, method='GET', **kw):
    headers = kw.pop('headers', {})
    token = app.storage.user.get('token')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return requests.request(method, f'{API_BASE}{path}', headers=headers, **kw)

# ---------- session helpers ----------
def set_user(token: str | None, user: dict | None):
    if token and user:
        app.storage.user['token'] = token
        app.storage.user['user']  = user
    else:
        app.storage.user.pop('token', None)
        app.storage.user.pop('user', None)

def signout():
    set_user(None, None)
    ui.notify('Signed out')
    ui.navigate.to('/signin')

# ---------- common header ----------
def header():
    with ui.header().classes('shadow-sm bg-white'):
        ui.label('🩺 NutriScope AI').classes('text-emerald-700 text-xl')
        with ui.row().classes('ml-auto'):
            ui.link('Home', '/')
            ui.link('Upload', '/upload')
            ui.link('Reports', '/reports')
            ui.link('About', '/about')
            user = app.storage.user.get('user')
            if user:
                ui.label(user.get('name', ''))
                ui.button('Sign Out', on_click=signout)
            else:
                ui.link('Sign In', '/signin')
                ui.link('Sign Up', '/signup')

# ---------- pages ----------
@ui.page('/')
def landing():
    header()
    with ui.column().classes('items-center justify-center pt-12 text-center'):
        ui.label('AI-assisted lab report insights').classes('text-4xl font-bold mb-2')
        ui.label('Upload your lab PDF, get a clear summary and a personalized meal plan backed by RAG.').classes('text-lg text-slate-600 mb-6')
        # Show greeting with name if available
        name = ''
        if app.storage.user.get('user'):
            name = app.storage.user.get('user', {}).get('name', '')
        elif app.storage.user.get('signup_name'):
            name = app.storage.user.get('signup_name')
        if name:
            ui.label(f"Hi {name}!").classes('text-xl font-semibold text-emerald-700 mb-2')
        if app.storage.user.get('user'):
            with ui.row().classes('gap-4 mb-4 justify-center'):
                ui.button('UPLOAD A REPORT', on_click=lambda: ui.navigate.to('/upload')).classes('bg-green-600 text-white rounded-lg px-6 py-2 text-base')
                ui.button('VIEW REPORTS', on_click=lambda: ui.navigate.to('/reports')).classes('bg-white border border-green-600 text-green-600 rounded-lg px-6 py-2 text-base')
        else:
            with ui.row().classes('gap-4 mb-4 justify-center'):
                ui.button('Sign in', on_click=lambda: ui.navigate.to('/signin')).classes('bg-green-600 text-white rounded-lg px-6 py-2 text-base')
                ui.button('Create account', on_click=lambda: ui.navigate.to('/signup')).classes('bg-white border border-green-600 text-green-600 rounded-lg px-6 py-2 text-base')
@ui.page('/about')
def about():
    header()

    with ui.column().classes('max-w-4xl mx-auto q-gutter-md px-4 pb-10'):
        ui.label('About').classes('text-3xl font-bold')

        ui.markdown(
            """
NutriScope AI helps you turn **lab PDFs** into clear summaries and **personalized meal plans**.  
It transforms complex reports into actionable guidance within seconds.

**What it does**
- Highlights what’s out of range and why it matters
- Explains results in plain language (no medical jargon)
- Generates tailored nutrition suggestions backed by RAG
- Keeps your data private: analysis runs on your machine / server

**Why NutriScope AI?**
- ⚡ Instant clarity → no guessing what results mean  
- 🧠 Simple explanations for complex lab data  
- 🍽️ Personalized nutrition → meal ideas built around your results  
- 🔒 Secure & private → your health data stays yours

With NutriScope AI, patients and families no longer need to Google symptoms or guess what their results mean. 
Doctors and nutritionists can use it as a supportive tool to quickly translate diagnostics into **actionable lifestyle choices**.
            """
        ).classes('text-[15px] leading-6')

        with ui.card().classes('rounded-2xl shadow-sm bg-[#f8fafc] p-5'):
            ui.label('Credits').classes('text-lg font-semibold mb-2')
            ui.markdown(
                "This platform was developed by **Venkata Sai Krishna Aditya Vatturi**."
            )
            with ui.row().classes('q-gutter-sm items-center'):
                ui.link('LinkedIn', 'https://www.linkedin.com/in/vvs-krishna-aditya-2002vvsk/', new_tab=True)
                ui.link('GitHub', 'https://github.com/vvskad1', new_tab=True)
                ui.link('Devpost', 'https://devpost.com/vvatturi?ref_content=user-portfolio&ref_feature=portfolio&ref_medium=global-nav&_gl=1*1mkqhmt*_gcl_au*ODMyODE0MDcyLjE3NTcxMTcwODE.*_ga*MTM1MjY5NTUwNC4xNzU3MTE3MDgx*_ga_0YHJK3Y10M*czE3NTcxMTcwODEkbzEkZzEkdDE3NTcxMTczNDkkajI2JGwwJGgw', new_tab=True)

        with ui.row().classes('justify-between items-center pt-6 text-sm text-slate-500'):
            ui.markdown('Developed by **Venkata Sai Krishna Aditya Vatturi**')
            with ui.row().classes('q-gutter-sm'):
                ui.link('Home', '/')
                ui.link('Upload', '/upload')
                ui.link('Reports', '/reports')


@ui.page('/signin')
def signin():
    header()
    email = ui.input('Email').classes('w-full max-w-md')
    pw = ui.input('Password', password=True, password_toggle_button=True).classes('w-full max-w-md')

    def go():
        r = api('/api/auth/login', 'POST', json={'email': email.value, 'password': pw.value})
        if r.ok:
            j = r.json()
            set_user(j.get('token'), j.get('user'))
            ui.notify('Signed in')
            ui.navigate.to('/')
        else:
            ui.notify(r.text, type='warning')

    ui.button('Sign in', on_click=go)


@ui.page('/signup')
def signup():
    header()
    with ui.card().classes('rounded-3xl shadow-lg bg-gradient-to-br from-white to-emerald-50 p-8 max-w-md mx-auto mt-12'):
        ui.label('Create your account').classes('text-2xl font-bold mb-1')
        ui.label('Upload and summarize lab reports securely').classes('text-base text-slate-600 mb-4')
        name = ui.input('Full name*').classes('w-full mb-2')
        email = ui.input('Email*').classes('w-full mb-2')
        pw = ui.input('Password*', password=True, password_toggle_button=True).classes('w-full mb-4')
        ui.label('Minimum 8 characters is recommended.').classes('text-xs text-slate-400 mb-2')
        def go():
            r = api('/api/auth/signup', 'POST', json={'name': name.value, 'email': email.value, 'password': pw.value})
            if r.ok:
                app.storage.user['signup_name'] = name.value  # Store name for greeting
                ui.notify('Account created!')
                ui.navigate.to('/signin')
            else:
                ui.notify(r.text, type='warning')
        ui.button('Create account', on_click=go).classes('w-full bg-emerald-700 text-white rounded-lg py-2 text-base mt-2')
        ui.markdown('Already have an account? [Sign in](/signin)').classes('mt-3 text-center text-sm')
@ui.page('/upload')
def upload():
    header()
    if not app.storage.user.get('token'):
        ui.navigate.to('/signin')
        return

    with ui.column().classes('items-center justify-center min-h-[70vh]'):
        with ui.card().classes('rounded-3xl shadow-lg bg-gradient-to-br from-white to-emerald-50 p-8 max-w-lg w-full'):
            ui.label('Upload a Lab Report').classes('text-2xl font-bold mb-1')
            ui.label('Get instant analysis and meal plan suggestions').classes('text-base text-slate-600 mb-4')
            report_name = ui.input('Report name*').classes('w-full mb-2')
            age         = ui.input('Age*').classes('w-full mb-2')
            sex         = ui.select(['Male', 'Female'], label='Gender*').classes('w-full mb-4')

            file_bytes = {'data': None}
            file_name  = {'name': None}

            def on_pick(e):
                file_bytes['data'] = e.content   # bytes
                file_name['name']  = e.name
                ui.notify(f'Selected: {e.name}')

            ui.upload(on_upload=on_pick, auto_upload=True).props('accept=.pdf').classes('mb-4')

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

            ui.button('Upload & Analyze', on_click=submit).classes('w-full bg-emerald-700 text-white rounded-lg py-2 text-base mt-2')

@ui.page('/reports')
def reports():
    header()

    if not app.storage.user.get('token'):
        ui.navigate.to('/signin')
        return

    r = api('/api/reports', 'GET', params={'page': 1, 'page_size': 8})

    # Show errors instead of blank page
    if not r.ok:
        with ui.column().classes('items-center justify-center min-h-[60vh]'):
            ui.label(f'Failed to load reports: {r.status_code}').classes('text-red-700')
            ui.label(r.text[:400]).classes('text-red-500 text-sm')
            with ui.row().classes('mt-2'):
                ui.link('Upload a report', '/upload')
                ui.link('Back to Home', '/')
        return

    try:
        data = r.json()
    except Exception:
        with ui.column().classes('items-center justify-center min-h-[60vh]'):
            ui.label('Server returned non-JSON for /api/reports').classes('text-red-700')
            ui.label(r.text[:400]).classes('text-red-500 text-sm')
        return

    # Accept various shapes: {"items":[...]}, {"reports":[...]}, or [...]
    if isinstance(data, dict):
        items = data.get('items') or data.get('reports') or []
    elif isinstance(data, list):
        items = data
    else:
        items = []

    if not items:
        with ui.column().classes('items-center justify-center min-h-[60vh]'):
            ui.label('No reports yet.').classes('text-slate-600')
            ui.link('Upload a report', '/upload')
        return

    with ui.column().classes('max-w-3xl mx-auto w-full gap-4 py-6'):
        for it in items:
            rid = it.get('id') or it.get('report_id')
            filename = it.get('filename') or it.get('name') or 'report.pdf'
            status = it.get('status') or 'done'
            with ui.card().classes('rounded-2xl shadow bg-white p-5 flex flex-col md:flex-row items-center justify-between'):
                with ui.column().classes('flex-1'):
                    ui.label(filename).classes('font-medium text-lg')
                    ui.label(status).classes('text-slate-500 text-sm')
                with ui.row().classes('gap-2'):
                    if rid is not None:
                        ui.button('Open', on_click=lambda r=rid: ui.navigate.to(f'/report/{r}')).classes('bg-emerald-600 text-white rounded-lg px-4 py-1')
                    def delete(r=rid):
                        d = api(f'/api/report/{r}', 'DELETE')
                        ui.notify('Deleted' if d.ok else d.text)
                        ui.run_javascript('location.reload()')
                    ui.button('Delete', on_click=delete).classes('bg-red-600 text-white rounded-lg px-4 py-1')

@ui.page('/report/{rid}')
def report(rid: str):
    header()
    if not app.storage.user.get('token'):
        ui.navigate.to('/signin')
        return

    r = api(f'/api/report/{rid}')
    rep = r.json() if r.ok else {}
    import json as _json
    ui.run_javascript(f"console.log('Report API response:', { _json.dumps(rep) })")

    with ui.column().classes('items-center justify-center min-h-[70vh]'):
        ui.label('Document Analysis').classes('text-2xl font-bold mb-2')
        ui.label(rep.get('filename', '')).classes('text-base text-slate-600 mb-4')

        # --- Structured summary first ---
        with ui.card().classes('rounded-2xl shadow-lg bg-gradient-to-br from-white to-sky-50 p-6 min-w-[350px] max-w-2xl w-full mb-6'):
            ui.label('Summary').classes('font-bold text-lg mb-2 text-sky-700')
            per_test = rep.get('per_test') or []
            disclaimer = rep.get('disclaimer') or "⚠️ NutriScope is an AI-powered tool designed to help you understand your lab reports. We use standard reference ranges for children, adults, and elderly patients, which may differ slightly from your testing laboratory’s ranges. Information and diet suggestions are educational only and should not replace consultation with a qualified healthcare professional."
            if per_test:
                lows = [t for t in per_test if t.get('status','').lower().startswith('low')]
                highs = [t for t in per_test if t.get('status','').lower().startswith('high')]
                normals = [t for t in per_test if t.get('status','').lower() == 'normal']
                # What's Low
                if lows:
                    ui.label("What's Low").classes('font-semibold text-base text-red-700 mt-2')
                    for t in lows:
                        with ui.column().classes('mb-2 pl-2'):
                            ui.markdown(f"**{t.get('test','')}**: {t.get('value','')} {t.get('unit','')}").classes('text-sm')
                            if t.get('importance'):
                                ui.markdown(f"*Why important*: {t['importance']}").classes('text-xs')
                            if t.get('why_low'):
                                ui.markdown(f"*Why low*: {'; '.join(t['why_low'])}").classes('text-xs')
                            if t.get('risks_if_low'):
                                ui.markdown(f"*Risks if neglected*: {'; '.join(t['risks_if_low'])}").classes('text-xs')
                            if t.get('next_steps'):
                                ui.markdown(f"*How to improve*: {'; '.join(t['next_steps'])}").classes('text-xs')
                # What's High
                if highs:
                    ui.label("What's High").classes('font-semibold text-base text-orange-700 mt-4')
                    for t in highs:
                        with ui.column().classes('mb-2 pl-2'):
                            ui.markdown(f"**{t.get('test','')}**: {t.get('value','')} {t.get('unit','')}").classes('text-sm')
                            if t.get('importance'):
                                ui.markdown(f"*Why important*: {t['importance']}").classes('text-xs')
                            if t.get('why_high'):
                                ui.markdown(f"*Why high*: {'; '.join(t['why_high'])}").classes('text-xs')
                            if t.get('risks_if_high'):
                                ui.markdown(f"*Risks if neglected*: {'; '.join(t['risks_if_high'])}").classes('text-xs')
                            if t.get('next_steps'):
                                ui.markdown(f"*How to improve*: {'; '.join(t['next_steps'])}").classes('text-xs')
                # Normals
                if normals:
                    ui.label('Normal Results').classes('font-semibold text-base text-emerald-700 mt-4')
                    ui.markdown(", ".join([f"{t.get('test','')} ({t.get('value','')} {t.get('unit','')})" for t in normals]) + ". Keep up the good habits!").classes('text-sm')
                if not (lows or highs or normals):
                    ui.label('No summary yet.').classes('text-slate-500')
                # Disclaimer
                ui.markdown(f"<div class='text-xs text-slate-500 mt-4'>{disclaimer}</div>")
            else:
                ui.label('No summary yet.').classes('text-slate-500')
                ui.markdown(f"<div class='text-xs text-slate-500 mt-4'>{disclaimer}</div>")

        # --- Meal plan next ---
        plan = rep.get('ai_meal_plan') or rep.get('diet_plan') or {}
        meals = plan.get('meals') or plan.get('add') or []
        with ui.card().classes('rounded-2xl shadow-lg bg-gradient-to-br from-white to-emerald-50 p-6 min-w-[350px] max-w-2xl w-full'):
            ui.label('Meal Plan').classes('font-bold text-lg mb-2 text-emerald-700')
            if meals:
                for m in meals:
                    ui.label(m.get('title') if isinstance(m, dict) else str(m)).classes('text-base mb-1')
            else:
                ui.label('No meal plan yet.').classes('text-slate-500')

        ui.link('Back', '/reports').classes('mt-6 text-emerald-700 text-base')

ui.run(storage_secret='please-change-this')  # enables per-user persistent storage
