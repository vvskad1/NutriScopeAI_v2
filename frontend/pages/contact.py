
from nicegui import ui
from components.header import header
from components.footer import footer

@ui.page('/contact')
def contact_page():
    header()
    with ui.column().classes('items-center justify-center min-h-[80vh] w-full'):
        with ui.column().classes('items-center justify-center w-full max-w-2xl mx-auto text-center'):
            ui.label('Contact Us').classes('text-3xl font-bold mb-1 font-sans')
            ui.label('If you have any questions, feedback, or need support, please use the form below or email us at support@nutriscope.ai').classes('text-base text-slate-600 mb-4 font-sans')
            ui.label('Your Name').classes('text-green-700 font-semibold w-full text-left')
            name = ui.input('Enter your name').classes('w-full mb-2 border-green-300')
            ui.label('Your Email').classes('text-green-700 font-semibold w-full text-left')
            email = ui.input('Enter your email').classes('w-full mb-2 border-green-300')
            ui.label('Message').classes('text-green-700 font-semibold w-full text-left')
            message = ui.textarea('Type your message here...').classes('w-full mb-4 border-green-300')
            import httpx
            async def submit():
                try:
                    url = "http://127.0.0.1:8000/api/contact"
                    headers = {"Content-Type": "application/json"}
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            url,
                            json={
                                'name': name.value,
                                'email': email.value,
                                'message': message.value
                            },
                            headers=headers
                        )
                    if resp.status_code == 200 and resp.json().get('success'):
                        ui.notify('Thank you for contacting us! We will get back to you soon.', color='green')
                        name.value = ''
                        email.value = ''
                        message.value = ''
                    else:
                        ui.notify('Failed to send message. Please try again later.', color='red')
                except Exception as e:
                    ui.notify(f'Error: {e}', color='red')
            ui.button('Send', on_click=submit).classes('w-full rounded-full py-3 text-base mt-2 font-semibold shadow').style('background-color:#059669 !important;color:#fff !important;border:none !important;')
    footer()
