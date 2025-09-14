from nicegui import ui
from components.header import header
from components.footer import footer

@ui.page('/about')
def about():
    header()
    with ui.column().classes('max-w-5xl mx-auto px-4 pb-10 min-h-[80vh] flex flex-col justify-center items-center'):
        ui.label('NutriScope AI').classes('text-4xl font-bold text-emerald-700 mb-4')
        with ui.card().classes('rounded-2xl shadow-lg bg-white p-8 mb-8 w-full'):
            ui.label('About').classes('text-2xl font-semibold mb-2 text-emerald-800')
            ui.markdown('''
NutriScope AI is an end-to-end platform that transforms complex lab reports (PDFs) into clear, actionable health summaries and personalized meal plans. Designed for patients, caregivers, and health professionals, it bridges the gap between raw lab data and practical, everyday nutrition.
            ''').classes('text-base leading-6 text-slate-700 mb-4')
            ui.label('Mission').classes('text-xl font-semibold mb-1 text-emerald-700')
            ui.markdown('''
To empower everyone to understand their health data and take actionable steps toward better nutrition and well-being—instantly, privately, and with confidence.
            ''').classes('text-base text-slate-700 mb-4')
            ui.label('Vision').classes('text-xl font-semibold mb-1 text-emerald-700')
            ui.markdown('''
To make lab results as easy to understand and act on as a recipe—democratizing health insights for all.
            ''').classes('text-base text-slate-700 mb-4')
            ui.label('Features').classes('text-xl font-semibold mb-1 text-emerald-700')
            ui.markdown('''
- Upload lab PDF and get instant, plain-language summaries
- Highlights abnormal results and explains their significance
- Personalized meal plans based on your unique lab profile
- Actionable suggestions for improving key health markers
- Secure: all analysis runs on your device/server—your data stays private
            ''').classes('text-base text-slate-700 mb-4')
            ui.label('Technologies Used').classes('text-xl font-semibold mb-1 text-emerald-700')
            ui.markdown('''
- **Frontend:** NiceGUI (Python), Tailwind-inspired utility classes
- **Backend:** FastAPI (Python), custom PDF parser, LLM (GROQ), RAG (Retrieval-Augmented Generation)
- **Storage:** JSON/SQLite for user and report data
- **Other:** ORJSON for fast serialization, custom KB loader, session management
            ''').classes('text-base text-slate-700 mb-4')
            ui.label('How It Works').classes('text-xl font-semibold mb-1 text-emerald-700')
            ui.markdown('''
1. **Upload:** User uploads a lab report PDF
2. **Extraction:** Backend parses and extracts test results
3. **Analysis:** LLM and RAG modules generate a summary and meal plan
4. **Presentation:** Frontend displays results in a modern, user-friendly UI
5. **Privacy:** All processing can be run locally for maximum data security
            ''').classes('text-base text-slate-700 mb-4')
            ui.label('Why NutriScope AI?').classes('text-xl font-semibold mb-1 text-emerald-700')
            with ui.column().classes('text-base text-slate-700 mb-4'):
                ui.label('Instant clarity—no guessing what results mean')
                ui.label('Simple explanations for complex lab data')
                ui.label('Personalized nutrition—meal ideas built around your results')
    footer()
