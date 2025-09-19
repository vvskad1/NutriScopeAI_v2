# --- Static files registration ---
import os
from nicegui import ui, app

# Import all modularized pages to register their routes
import pages.home
import pages.reports
import pages.upload
import pages.signin
import pages.signup

import pages.about
import pages.report_details
import pages.contact

from utils import api, set_user, signout
print("Starting NiceGUI app...")
static_dir = os.path.join(os.path.dirname(__file__), 'static')
app.add_static_files('/static', static_dir)

# Ensure NiceGUI server starts (must be last line)
ui.run(storage_secret="b7f3e2c1-4a9d-4e8a-9c2b-7d1e5f6a8c9e")