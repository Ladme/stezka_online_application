import os
import smtplib
from email.message import EmailMessage

from stezka_online_application._cfg import (
    CHIEF_EMAIL,
    CHIEF_EMAIL_BODY,
    GUARDIAN_EMAIL_BODY,
    MULTIPLE_CHILDREN_EMAIL_NOTE,
    SENDER,
    SMTP_HOST,
    SMTP_PORT,
)
from stezka_online_application._export import to_csv, to_yaml
from stezka_online_application._models import Application


def _password() -> str:
    """Read the SMTP password from the environment."""
    password = os.environ.get("SMTP_PASSWORD")
    if not password:
        message = "SMTP_PASSWORD is not set (expected in the .env file)"
        raise RuntimeError(message)
    return password


def _summary(application: Application) -> str:
    return "\n".join(
        f"- {child.name}, nar. {child.birth_date.strftime('%d.%m.%Y')}, "
        f"{child.address.street}, {child.address.city}"
        for child in application.children
    )


def _guardian_message(application: Application, pdf: bytes) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "Přihláška do oddílu 48. PTO Stezka"
    message["From"] = SENDER
    message["To"] = application.guardian.email

    note = MULTIPLE_CHILDREN_EMAIL_NOTE if len(application.children) > 1 else ""
    message.set_content(
        GUARDIAN_EMAIL_BODY.format(
            summary=_summary(application),
            chief_email=CHIEF_EMAIL,
            signature_note=note,
        )
    )

    message.add_attachment(
        pdf, maintype="application", subtype="pdf", filename="prihlaska.pdf"
    )

    return message


def _chief_message(application: Application, pdf: bytes) -> EmailMessage:
    guardian = application.guardian
    message = EmailMessage()
    message["Subject"] = f"[Stezka] Nová přihláška: {guardian.person}"
    message["From"] = SENDER
    message["To"] = CHIEF_EMAIL
    message["Reply-To"] = guardian.email

    message.set_content(
        CHIEF_EMAIL_BODY.format(
            guardian=guardian.person,
            email=guardian.email,
            phone=guardian.phone,
            summary=_summary(application),
        )
    )

    message.add_attachment(
        to_yaml(application).encode(),
        maintype="application",
        subtype="yaml",
        filename="prihlaska.yaml",
    )

    message.add_attachment(
        to_csv(application).encode("utf-8-sig"),
        maintype="text",
        subtype="csv",
        filename="prihlaska.csv",
    )
    message.add_attachment(
        pdf, maintype="application", subtype="pdf", filename="prihlaska.pdf"
    )
    return message


def send_application(application: Application, pdf: bytes) -> None:
    """Send both e-mails over one SMTP connection. Blocking."""
    messages = [_guardian_message(application, pdf), _chief_message(application, pdf)]
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(SENDER, _password())
        for message in messages:
            smtp.send_message(message)
