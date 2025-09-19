import smtplib
from email.mime.text import MIMEText
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os

router = APIRouter()

SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', 'vvskaditya123@gmail.com')
SMTP_PASS = os.getenv('SMTP_PASS', 'haom tgmr jupj syts')

@router.post('/contact')
async def contact_email(request: Request):
    data = await request.json()
    name = data.get('name', '')
    email = data.get('email', '')
    message = data.get('message', '')
    subject = f'NutriScope Contact Form: {name or "No Name"}'
    body = f'Name: {name}\nEmail: {email}\n\nMessage:\n{message}'
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = SMTP_USER
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, SMTP_USER, msg.as_string())
        return JSONResponse({'success': True, 'message': 'Email sent successfully.'})
    except Exception as e:
        print(f'[EMAIL DEBUG] Failed to send email: {e}')
        return JSONResponse({'success': False, 'message': f'Failed to send email: {e}'}, status_code=500)
