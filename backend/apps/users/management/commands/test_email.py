import smtplib
import ssl

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test SMTP configuration by sending a test email."

    def add_arguments(self, parser):
        parser.add_argument("to", help="Recipient email address")

    def handle(self, *args, **options):
        to = options["to"]

        self.stdout.write("\n--- SMTP settings Django will use ---")
        self.stdout.write(f"  HOST     : {settings.EMAIL_HOST}")
        self.stdout.write(f"  PORT     : {settings.EMAIL_PORT}")
        self.stdout.write(f"  USER     : {settings.EMAIL_HOST_USER!r}")
        self.stdout.write(f"  PASSWORD : {'(empty)' if not settings.EMAIL_HOST_PASSWORD else settings.EMAIL_HOST_PASSWORD[:12] + '...' + settings.EMAIL_HOST_PASSWORD[-4:]}")
        self.stdout.write(f"  USE_TLS  : {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"  FROM     : {settings.DEFAULT_FROM_EMAIL!r}")
        self.stdout.write(f"  TO       : {to}")
        self.stdout.write("")

        # Raw SMTP test so we see exactly what Brevo responds
        self.stdout.write("--- Connecting directly via smtplib ---")
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=10) as server:
                server.set_debuglevel(1)
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                msg = (
                    f"From: {settings.DEFAULT_FROM_EMAIL}\r\n"
                    f"To: {to}\r\n"
                    f"Subject: TalentExe SMTP test\r\n\r\n"
                    "This is a test email from the TalentExe test_email management command."
                )
                server.sendmail(settings.EMAIL_HOST_USER, [to], msg)
            self.stdout.write(self.style.SUCCESS("\nSMTP test PASSED — email sent."))
        except smtplib.SMTPAuthenticationError as e:
            self.stdout.write(self.style.ERROR(f"\nAuthentication failed: {e}"))
            self.stdout.write(
                "  → The SMTP_USER or SMTP_PASSWORD is wrong.\n"
                "  → Log in to Brevo → SMTP & API → SMTP tab → regenerate the key\n"
                "    and update BREVO_SMTP_PASSWORD in backend/.env"
            )
        except smtplib.SMTPException as e:
            self.stdout.write(self.style.ERROR(f"\nSMTP error: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nConnection error: {e}"))
