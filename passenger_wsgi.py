"""Point d'entrée pour Passenger (cPanel « Setup Python App » sur o2switch)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_chatbot.settings")

from django_chatbot.wsgi import application  # noqa: E402,F401
