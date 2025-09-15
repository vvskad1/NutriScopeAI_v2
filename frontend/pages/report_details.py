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
                    ]
                    ui.add_head_html('<style>.q-table th, .q-table__th { font-weight: bold !important; }</style>')
                    rows = []
                    import re
                    def clean_llm_text(val):
                        if not isinstance(val, str):
                            return val
                        def collapse_single_chars(s):
                            return re.sub(r'(?:\b\w\b[ ]*){2,}', lambda m: m.group(0).replace(' ', ''), s)
                        prev = None
                        while prev != val:
                            prev = val
                            val = collapse_single_chars(val)
                        val = re.sub(r'(?<=\b\w) (?=\w\b)', '', val)
                        val = re.sub(r'\s{2,}', ' ', val)
                        return val.strip()

                    def is_concatenated(text):
                        # Heuristic: if there are more than 20 letters in a row with no space, flag as concatenated
                        return bool(re.search(r'[a-zA-Z]{20,}', text))
                    warning_shown = False
                    for t in per_test:
                        test = clean_llm_text((t.get('test') or t.get('name') or t.get('title') or 'Unknown Test') + f" ({t.get('value','')} {t.get('unit','')})")
                        status = clean_llm_text(t.get('status','').capitalize())
                        importance = clean_llm_text(t.get('importance',''))
                        # Support both new and old backend formats
                        status_lower = t.get('status','').lower()
                        reason = ''
                        if 'reason' in t and isinstance(t['reason'], str) and t['reason']:
                            reason = clean_llm_text(t['reason'])
                        elif status_lower == 'low' and t.get('reason_low'):
                            reason = clean_llm_text(str(t['reason_low']))
                        elif status_lower == 'high' and t.get('reason_high'):
                            reason = clean_llm_text(str(t['reason_high']))
                        risks = ''
                        if 'risks' in t and isinstance(t['risks'], str) and t['risks']:
                            risks = clean_llm_text(t['risks'])
                        # For legacy support, also check risks_if_low/risks_if_high
                        elif status_lower == 'low' and t.get('risks_if_low'):
                            risks = clean_llm_text(str(t['risks_if_low']))
                        elif status_lower == 'high' and t.get('risks_if_high'):
                            risks = clean_llm_text(str(t['risks_if_high']))
                        if (is_concatenated(reason) or is_concatenated(risks)) and not warning_shown:
                            ui.notify('⚠️ Some AI-generated text is not readable. Please try regenerating the report or contact support.', color='warning')
                            warning_shown = True
                        rows.append({
                            'test': test,
                            'status': status,
                            'importance': importance,
                            'reason': reason,
                            'risks': risks,
                        })
                    # Add custom CSS for table cell wrapping and normal font style (force inherit from table)
                    ui.add_head_html('''<style>
                        .q-table__td, .q-table__td * {
                            white-space: pre-line;
                            word-break: break-word;
                            font-family: inherit;
                            font-size: inherit;
                            font-weight: inherit;
                            letter-spacing: normal;
                        }
                        .q-table {
                            font-family: Arial, Helvetica, sans-serif;
                            font-size: 1rem;
                            font-weight: 400;
                        }
                    </style>''')
                    with ui.table(
                        columns=columns,
                        rows=rows,
                        row_key='test',
                        ) as table:
                        table.props('wrap-cells')
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
                        for_tests_list = [str(x) for x in meal['for_tests']]
                        ui.label('Supports tests: ' + ', '.join(for_tests_list)).classes('text-xs text-yellow-600 mt-1')
        else:
            with ui.row().classes('justify-center'):
                ui.icon('warning').classes('text-yellow-500 text-2xl')
                ui.label('No meal plan suggestions available for this report.').classes('text-yellow-600 text-lg font-semibold')
