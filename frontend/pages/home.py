
from nicegui import ui, app
from components.header import header
from components.footer import footer
from app_nicegui import api

@ui.page('/')
def landing():
    # Add background image CSS for homepage
    header()
    with ui.column().classes('items-center justify-center pt-16 text-center max-w-4xl mx-auto px-4 pb-10'):
        ui.label('AI-assisted lab report insights').classes('text-5xl font-bold mb-3 font-sans')
        ui.label('Upload your lab PDF, get a clear summary and a personalized meal plan backed by RAG.').classes('text-lg text-slate-600 mb-8 font-sans')
        # Buttons
        with ui.row().classes('justify-center gap-4 mb-4'):
            ui.button('UPLOAD A REPORT', on_click=lambda: ui.navigate.to('/upload')).classes('rounded-full px-6 py-2 text-lg font-semibold shadow').style('background-color:#059669 !important;color:#fff !important;border:none !important;')
            ui.button('VIEW REPORTS', on_click=lambda: ui.navigate.to('/reports')).classes('rounded-full px-6 py-2 text-lg font-semibold shadow').style('background-color:#fff !important;color:#059669 !important;border:2px solid #059669 !important;')
        # Welcome message
        name = ''
        if app.storage.user.get(str('user')):
            name = app.storage.user.get(str('user'), {}).get('name', '')
        elif app.storage.user.get(str('signup_name')):
            name = app.storage.user.get(str('signup_name'))
        if name:
            ui.label(f"Welcome, {name}").classes('text-xl font-semibold text-emerald-700 mb-2')
    # Floating Nurse AI Chatbot Button and Dialog (homepage only, above footer)
    ui.add_head_html('''
    <style>
    #nurse-fab {
        position: fixed;
        right: 32px;
        bottom: 160px;
        z-index: 9999;
        background: #059669 !important;
        color: #fff !important;
        border-radius: 50% !important;
        width: 64px !important;
        height: 64px !important;
        box-shadow: 0 4px 16px #0002 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 2rem !important;
        cursor: pointer !important;
        border: none !important;
        transition: background 0.2s !important;
        animation: nurse-fab-pulse 1.2s infinite alternate;
    }
    @keyframes nurse-fab-pulse {
        0% { box-shadow: 0 0 0 0 #05966955; }
        100% { box-shadow: 0 0 0 16px #05966911; }
    }
    #nurse-fab:hover { background: #047857 !important; }
    #nurse-fab .nicegui-icon {
        color: #fff !important;
        background: #059669 !important;
        border-radius: 50% !important;
        width: 44px !important;
        height: 44px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 2rem !important;
        margin: 0 auto !important;
    }
    #nurse-fab-label {
        position: fixed;
        right: 110px;
        bottom: 170px;
        z-index: 10000;
        background: #fff;
        color: #059669;
        font-weight: bold;
        font-size: 1.1rem;
        padding: 10px 18px;
        border-radius: 18px;
        box-shadow: 0 2px 12px #0002;
        border: 2px solid #05966922;
        display: flex;
        align-items: center;
        gap: 8px;
        animation: nurse-fab-label-pop 1.2s infinite alternate;
    }
    @keyframes nurse-fab-label-pop {
        0% { transform: scale(1); }
        100% { transform: scale(1.06); }
    }
    .nurse-chat-dialog .nicegui-dialog > .nicegui-column {
        gap: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        background: #ece5dd;
        border-radius: 18px;
        box-shadow: 0 8px 32px #0002;
        min-width: 350px;
        max-width: 98vw;
        width: 370px;
        min-height: 340px;
        overflow: hidden;
    }
    .nurse-chat-header {
        background: #059669;
        color: #fff;
        padding: 14px 18px;
        font-size: 1.1rem;
        font-weight: bold;
        border-top-left-radius: 18px;
        border-top-right-radius: 18px;
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
        box-sizing: border-box;
        margin-bottom: 0;
    }
    .nurse-chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 10px 10px 10px 10px;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        background: #ece5dd;
        width: 100%;
        box-sizing: border-box;
        margin: 0;
        min-height: 180px;
        max-height: 320px;
    }
    .nurse-chat-bubble-user {
        align-self: flex-end;
        background: #dcf8c6;
        color: #222;
        border-radius: 18px 18px 4px 18px;
        padding: 10px 16px;
        max-width: 100%;
        min-width: 80px;
        font-size: 1rem;
        box-shadow: 0 2px 8px #0001;
        margin-bottom: 2px;
        position: relative;
        word-break: break-word;
        text-align: left;
        display: flex;
        align-items: center;
    }
    .nurse-chat-bubble-bot {
        align-self: flex-start;
        background: #fff;
        color: #059669;
        border-radius: 18px 18px 18px 4px;
        padding: 10px 16px;
        max-width: 100%;
        font-size: 1rem;
        box-shadow: 0 2px 8px #0001;
        margin-bottom: 2px;
        position: relative;
        word-break: break-word;
    }
    .nurse-chat-timestamp {
        font-size: 0.75rem;
        color: #888;
        margin-top: 2px;
        margin-bottom: 4px;
        text-align: right;
    }
    .nurse-chat-inputbar {
        display: flex;
        align-items: center;
        padding: 10px 12px;
        background: #f7f7f7;
        border-bottom-left-radius: 18px;
        border-bottom-right-radius: 18px;
        gap: 8px;
        border-top: 1px solid #e0e0e0;
        width: 100%;
        box-sizing: border-box;
    }
    .nurse-chat-inputbar input {
        flex: 1;
        border-radius: 20px;
        border: 1px solid #cfd8dc;
        padding: 8px 14px;
        font-size: 1rem;
        outline: none;
        background: #fff;
    }
    .nurse-chat-inputbar button, .nurse-chat-inputbar .nicegui-button {
        background: #059669 !important;
        color: #fff !important;
        border: none !important;
        border-radius: 50% !important;
        width: 44px !important;
        height: 44px !important;
        font-size: 1.3rem !important;
        margin-left: 0 !important;
        cursor: pointer !important;
        transition: background 0.2s !important;
        box-shadow: none !important;
        min-width: 44px !important;
    }
    .nurse-chat-inputbar button:hover, .nurse-chat-inputbar .nicegui-button:hover {
        background: #047857 !important;
    }
    .nurse-chat-close-btn {
        background: #059669 !important;
        color: #fff !important;
        border: none !important;
        border-radius: 50% !important;
        width: 32px !important;
        height: 32px !important;
        font-size: 1.1rem !important;
        margin-left: auto !important;
        cursor: pointer !important;
        transition: background 0.2s !important;
    }
    .nurse-chat-close-btn:hover { background: #047857 !important; }
    </style>
    ''')
    import datetime
    chat_dialog = [None]
    chat_history = []
    minimized = [False]
    def open_chat():
        minimized[0] = False
        if not chat_dialog[0]:
            chat_dialog[0] = ui.dialog().classes('nurse-chat-dialog')
            with chat_dialog[0]:
                with ui.column().classes('w-full h-full'):
                    # Header
                    with ui.row().classes('nurse-chat-header'):
                        ui.icon('medical_services').classes('mr-1')
                        ui.label('Nurse AI Assistant')
                        # Minimize button (chevron-down)
                        ui.button(icon='expand_more', on_click=lambda: minimize_chat()).classes('nurse-chat-close-btn ml-auto').tooltip('Minimize')
                    # Messages area
                    chat_box = ui.column().classes('nurse-chat-messages').style('flex:1;min-height:220px;')
                    # Input bar (same line)
                    with ui.element('div').classes('nurse-chat-inputbar').style('display:flex;align-items:center;gap:8px;width:100%;box-sizing:border-box;'):
                        chat_input = ui.input(placeholder='Type your message...').classes('').style('flex:1 1 auto;min-width:0;margin-right:8px;').props('autofocus')
                        def send_chat():
                            user_msg = chat_input.value.strip()
                            if not user_msg:
                                return
                            chat_history.append({'role': 'user', 'content': user_msg, 'timestamp': datetime.datetime.now().strftime('%H:%M')})
                            chat_input.value = ''
                            render_msgs()
                            print('[DEBUG] Sending chat_history:', chat_history)
                            try:
                                r = api('/api/chatbot', 'POST', json={'messages': chat_history})
                                print('[DEBUG] Response status:', r.status_code)
                                print('[DEBUG] Response text:', r.text)
                                if r.ok:
                                    bot_msg = r.json().get('response', 'Sorry, I could not answer that.')
                                else:
                                    bot_msg = 'Sorry, there was a problem contacting the nurse assistant.'
                            except Exception as e:
                                print('[DEBUG] Exception in send_chat:', e)
                                bot_msg = 'Sorry, there was a problem contacting the nurse assistant.'
                            chat_history.append({'role': 'assistant', 'content': bot_msg, 'timestamp': datetime.datetime.now().strftime('%H:%M')})
                            render_msgs()
                        def render_msgs():
                            chat_box.clear()
                            if not chat_history:
                                with chat_box:
                                    ui.label('How can I help you today?').classes('nurse-chat-bubble-bot')
                            for m in chat_history:
                                with chat_box:
                                    if m['role'] == 'user':
                                        with ui.row().classes('justify-end w-full'):
                                            with ui.column().classes('items-end'):
                                                ui.label(m['content']).classes('nurse-chat-bubble-user')
                                                ui.label(m.get('timestamp','')).classes('nurse-chat-timestamp')
                                    else:
                                        with ui.row().classes('justify-start w-full'):
                                            with ui.column().classes('items-start'):
                                                ui.label(m['content']).classes('nurse-chat-bubble-bot')
                                                ui.label(m.get('timestamp','')).classes('nurse-chat-timestamp')
                        render_msgs()
                        def on_enter(e):
                            if e.args and (e.args[0] == 'Enter' or e.args[0] == 'enter'):
                                send_chat()
                        chat_input.on('keydown.enter', lambda e: send_chat())
                        ui.button('➤', on_click=send_chat).classes('').style('width:44px;height:44px;border-radius:50%;background:#059669;color:#fff;display:flex;align-items:center;justify-content:center;font-size:1.3rem;min-width:44px;')
        chat_dialog[0].open()
    def minimize_chat():
        minimized[0] = True
        if chat_dialog[0]:
            chat_dialog[0].close()
    # If minimized, show a small button to restore
    def show_restore():
        if minimized[0]:
            ui.button(icon='expand_less', on_click=open_chat).props('id="nurse-fab"').tooltip('Restore Nurse AI')
    # Floating Action Button
    if not minimized[0]:
        with ui.element('div'):
            ui.button(icon='medical_services', on_click=open_chat).props('id="nurse-fab"').tooltip('Ask Nurse AI')
            ui.html('<div id="nurse-fab-label">💡 Need help? Ask Nurse AI!</div>')
    else:
        show_restore()
    footer()
