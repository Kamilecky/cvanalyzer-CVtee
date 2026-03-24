"""test_smtp.py — sprawdzenie połączenia SMTP z Mailgun (niezależnie od Django).

Uruchomienie:
    python test_smtp.py

Hasło SMTP podaj jako zmienną środowiskową:
    set MAILGUN_SMTP_PASSWORD=twoje_haslo
    python test_smtp.py

Lub zostaniesz poproszony o podanie hasła interaktywnie.
"""

import getpass
import os
import smtplib
import ssl

HOST  = "smtp.eu.mailgun.org"
PORT  = 465
LOGIN = "postmaster@mg.cveeto.eu"

password = os.environ.get("MAILGUN_SMTP_PASSWORD") or getpass.getpass("SMTP password: ")

context = ssl.create_default_context()

try:
    with smtplib.SMTP_SSL(HOST, PORT, context=context) as server:
        server.login(LOGIN, password)
        print("LOGIN OK — połączenie SMTP działa poprawnie")
except smtplib.SMTPAuthenticationError as e:
    print(f"ERROR: Błąd autoryzacji (złe hasło lub login) — {e}")
except smtplib.SMTPConnectError as e:
    print(f"ERROR: Nie można połączyć się z serwerem — {e}")
except Exception as e:
    print(f"ERROR: {e}")
