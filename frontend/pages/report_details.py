from nicegui import ui, app
from components.header import header
from components.footer import footer
from utils import api

@ui.page('/report/{rid}')
def report(rid: str):
    header()
    if not app.storage.user.get(str('token')):
        ui.navigate.to('/signin')
        return
    r = api(f'/api/report/{rid}')
    rep = r.json() if r.ok else {}
    with ui.column().classes('w-full items-center gap-8'):
        with ui.card().classes('rounded-2xl shadow-lg bg-gradient-to-br from-white to-sky-50 p-6 w-full max-w-5xl'):
            ui.label('Summary').classes('font-bold text-2xl mb-4 text-sky-700')
            per_test = rep.get('per_test') or []
            disclaimer = rep.get('disclaimer') or "⚠️ NutriScope is an AI-powered tool designed to help you understand your lab reports. We use standard reference ranges for children, adults, and elderly patients, which may differ slightly from your testing laboratory’s ranges. Information and diet suggestions are educational only and should not replace consultation with a qualified healthcare professional."
            if per_test:
                ui.label('Test Results Table').classes('font-semibold text-base text-sky-700 mt-2 mb-2')
                with ui.element('div').classes('w-full overflow-x-auto center-table-cells'):
                    columns = [
                        {'name': 'test', 'label': 'Test Name', 'field': 'test', 'sortable': True},
                        {'name': 'status', 'label': 'High/Low', 'field': 'status', 'sortable': True},
                        {'name': 'importance', 'label': 'Why Important', 'field': 'importance', 'sortable': False},
                        {'name': 'reason', 'label': 'Reason for High/Low', 'field': 'reason', 'sortable': False},
                        {'name': 'risks', 'label': 'Risks', 'field': 'risks', 'sortable': False},
                        {'name': 'improvements', 'label': 'Improvements', 'field': 'improvements', 'sortable': False},
                    ]
                    rows = []
                    for t in per_test:
                        rows.append({
                            'test': (t.get('test') or t.get('name') or t.get('title') or 'Unknown Test') + f" ({t.get('value','')} {t.get('unit','')})",
                            'status': t.get('status','').capitalize(),
                            'importance': t.get('importance',''),
                            'reason': '\n'.join(t.get('why_low',[]) if t.get('status','').lower() == 'low' else t.get('why_high',[])),
                            'risks': '\n'.join(t.get('risks_if_low',[]) if t.get('status','').lower() == 'low' else t.get('risks_if_high',[])),
                            'improvements': '\n'.join(t.get('next_steps',[])),
                        })
                    with ui.table(
                        columns=columns,
                        rows=rows,
                        row_key='test',
                    ):
                        pass
                ui.markdown(f"<div class='text-xs text-slate-500 mt-4'>{disclaimer}</div>")
            else:
                ui.label('No summary yet.').classes('text-slate-500')
                ui.markdown(f"<div class='text-xs text-slate-500 mt-4'>{disclaimer}</div>")
        add_meal_plan_card(rep)
    footer()

def add_meal_plan_card(rep):
    with ui.card().classes('rounded-2xl shadow-lg bg-gradient-to-br from-white to-yellow-100 p-6 w-full max-w-5xl'):
        ui.label('Personalized Meal Plan').classes('font-bold text-2xl mb-4 text-yellow-700')
        diet_plan = rep.get('diet_plan') or {}
        meals = diet_plan.get('meals') or []
        if meals:
            for meal in meals:
                with ui.card().classes('mb-4 bg-yellow-50 border border-yellow-200'):
                    ui.label(meal.get('name', 'Meal')).classes('font-semibold text-lg text-yellow-800')
                    ui.label('Ingredients:').classes('font-medium text-yellow-700 mt-2')
                    for ing in meal.get('ingredients', []):
                        ui.label(f"• {ing}").classes('text-slate-700 text-left pl-4')
                    ui.label('Instructions:').classes('font-medium text-yellow-700 mt-2')
                    ui.label(meal.get('instructions', '')).classes('text-slate-700')
                    if meal.get('why_this_meal'):
                        ui.label('Why this meal:').classes('font-medium text-yellow-700 mt-2')
                        ui.label(meal['why_this_meal']).classes('text-slate-700')
                    if meal.get('for_tests'):
                        ui.label('Supports tests: ' + ', '.join(meal['for_tests'])).classes('text-xs text-yellow-600 mt-1')
        else:
            with ui.row().classes('justify-center'):
                ui.icon('warning').classes('text-yellow-500 text-2xl')
                ui.label('No meal plan suggestions available for this report.').classes('text-yellow-600 text-lg font-semibold')
