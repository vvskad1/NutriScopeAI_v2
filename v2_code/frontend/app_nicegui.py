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
    ui.label('AI-assisted lab report insights').classes('text-2xl font-bold')
    if app.storage.user.get('user'):
        with ui.row():
            ui.link('Upload a report', '/upload')
            ui.link('View reports', '/reports')
    else:
        with ui.row():
            ui.link('Sign in', '/signin')
            ui.link('Create account', '/signup')

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
    name = ui.input('Full name').classes('w-full max-w-md')
    email = ui.input('Email').classes('w-full max-w-md')
    pw = ui.input('Password', password=True, password_toggle_button=True).classes('w-full max-w-md')

    def go():
        r = api('/api/auth/signup', 'POST', json={'name': name.value, 'email': email.value, 'password': pw.value})
        if r.ok:
            ui.notify('Account created!')
            ui.navigate.to('/signin')
        else:
            ui.notify(r.text, type='warning')

    ui.button('Create account', on_click=go)

@ui.page('/upload')
def upload():
    header()
    if not app.storage.user.get('token'):
        ui.navigate.to('/signin')
        return

    ui.label('Upload').classes('text-xl font-bold')

    report_name = ui.input('Report name').classes('w-full max-w-lg')
    age         = ui.input('Age').classes('w-full max-w-lg')
    sex         = ui.select(['Male', 'Female'], label='Gender').classes('w-full max-w-lg')

    file_bytes = {'data': None}
    file_name  = {'name': None}

    def on_pick(e):
        file_bytes['data'] = e.content   # bytes
        file_name['name']  = e.name
        ui.notify(f'Selected: {e.name}')

    # NOTE: pass callback via keyword 'on_upload'
    ui.upload(on_upload=on_pick, auto_upload=True).props('accept=.pdf')

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

    ui.button('Upload & Analyze', on_click=submit).classes('mt-3')

@ui.page('/reports')
def reports():
    header()

    if not app.storage.user.get('token'):
        ui.navigate.to('/signin')
        return

    r = api('/api/reports', 'GET', params={'page': 1, 'page_size': 8})

    # Show errors instead of blank page
    if not r.ok:
        ui.label(f'Failed to load reports: {r.status_code}').classes('text-red-700')
        ui.label(r.text[:400]).classes('text-red-500 text-sm')
        with ui.row().classes('mt-2'):
            ui.link('Upload a report', '/upload')
            ui.link('Back to Home', '/')
        return

    try:
        data = r.json()
    except Exception:
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
        ui.label('No reports yet.').classes('text-slate-600')
        ui.link('Upload a report', '/upload')
        return

    for it in items:
        rid = it.get('id') or it.get('report_id')
        filename = it.get('filename') or it.get('name') or 'report.pdf'
        status = it.get('status') or 'done'
        with ui.card():
            ui.label(filename).classes('font-medium')
            ui.label(status).classes('text-slate-500 text-sm')
            with ui.row():
                if rid is not None:
                    ui.button('Open', on_click=lambda r=rid: ui.navigate.to(f'/report/{r}'))
                def delete(r=rid):
                    d = api(f'/api/report/{r}', 'DELETE')
                    ui.notify('Deleted' if d.ok else d.text)
                    ui.run_javascript('location.reload()')
                ui.button('Delete', on_click=delete, color='negative')

@ui.page('/report/{rid}')
def report(rid: str):
    header()
    if not app.storage.user.get('token'):
        ui.navigate.to('/signin')
        return

    r = api(f'/api/report/{rid}')
    rep = r.json() if r.ok else {}

    ui.label('Document Analysis').classes('text-xl font-bold')
    ui.label(rep.get('filename', ''))

    plan = rep.get('ai_meal_plan') or rep.get('diet_plan') or {}
    meals = plan.get('meals') or plan.get('add') or []

    with ui.row():
        with ui.card():
            ui.label('Meal Plan').classes('font-bold')
            if meals:
                for m in meals:
                    ui.label(m.get('title') if isinstance(m, dict) else str(m))
            else:
                ui.label('No meal plan yet.')
        with ui.card():
            ui.label('Summary').classes('font-bold')
            ui.label(rep.get('ai_summary') or rep.get('summary_text') or 'No summary yet.')

    ui.link('Back', '/reports')

ui.run(storage_secret='please-change-this')  # enables per-user persistent storage
