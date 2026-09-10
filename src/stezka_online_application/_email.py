import os
import smtplib
from email.message import EmailMessage

from stezka_online_application._cfg import (
    BANK_ACCOUNT,
    CHIEF_EMAIL,
    CHIEF_EMAIL_BODY,
    MEMBERSHIP_FEE,
    MULTIPLE_CHILDREN_EMAIL_BODY,
    ONE_CHILD_EMAIL_BODY,
    SENDER,
    SMTP_HOST,
    SMTP_PORT,
)
from stezka_online_application._export import to_csv, to_yaml
from stezka_online_application._models import Application
from stezka_online_application._qr import payment_amount, payment_message


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


def _guardian_email_body(application: Application) -> str:
    template = (
        ONE_CHILD_EMAIL_BODY
        if len(application.children) == 1
        else MULTIPLE_CHILDREN_EMAIL_BODY
    )
    return template.format(
        summary=_summary(application),
        chief_email=CHIEF_EMAIL,
        amount=payment_amount(application),
        fee=MEMBERSHIP_FEE,
        account=BANK_ACCOUNT,
        payment_note=payment_message(application),
    )


def _guardian_message(
    application: Application, pdf: bytes, qr_code: bytes
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "Přihláška do oddílu 48. PTO Stezka"
    message["From"] = SENDER
    message["To"] = application.guardian.email

    message.set_content(_guardian_email_body(application))

    message.add_attachment(
        pdf, maintype="application", subtype="pdf", filename="prihlaska.pdf"
    )

    message.add_attachment(
        qr_code, maintype="image", subtype="png", filename="platba.png"
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


def send_application(application: Application, pdf: bytes, qr_code: bytes) -> None:
    """Send both e-mails over one SMTP connection. Blocking."""
    messages = [
        _guardian_message(application, pdf, qr_code),
        _chief_message(application, pdf),
    ]
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(SENDER, _password())
        for message in messages:
            smtp.send_message(message)
