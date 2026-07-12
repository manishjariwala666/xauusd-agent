"""Direct Streamlit route for the protected admin area.

This file lets ``/admin`` resolve cleanly in Streamlit Cloud/Railway instead
of showing Streamlit's generic "page not found" notice before the app router
decides whether to show login or the admin dashboard.
"""

from __future__ import annotations

from app import run


run()
