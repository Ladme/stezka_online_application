import io
import unicodedata
from collections.abc import Callable

from PIL import Image
from qrplatba import QRPlatbaGenerator

from stezka_online_application._cfg import CFG
from stezka_online_application._models import Application


def _ascii(value: str) -> str:
    """Strip diacritics: the payment message may only carry plain ASCII."""
    decomposed = unicodedata.normalize("NFKD", value)
    return decomposed.encode("ascii", "ignore").decode("ascii")


def _full_name(name: str) -> str:
    return name


def _short_surnames(name: str) -> str:
    """Jan Novák Dvořák -> Jan N D"""
    first, *surnames = name.split()
    return " ".join([first, *(f"{surname[0]}" for surname in surnames)])


def _initials(name: str) -> str:
    """Jan Novák Dvořák -> J N D."""
    return " ".join(f"{part[0]}" for part in name.split())


def payment_message(application: Application) -> str:
    """Payment message naming every child, shortened until it fits the SPAYD limit."""
    prefix = f"Registrace {CFG.fee.school_year} - "
    shortenings: tuple[Callable[[str], str], ...] = (
        _full_name,
        _short_surnames,
        _initials,
    )

    message = ""
    for shorten in shortenings:
        message = _ascii(
            prefix + ", ".join(shorten(child.name) for child in application.children)
        )
        if len(message) <= CFG.bank.message_limit:
            return message

    return message[: CFG.bank.message_limit]


def payment_amount(application: Application) -> int:
    """One fee per registered child."""
    return CFG.fee.amount * len(application.children)


def payment_qr_code(application: Application) -> bytes:
    """The payment as a PNG QR code, for the e-mail and the confirmation dialog."""
    generator = QRPlatbaGenerator(
        CFG.bank.account,
        amount=payment_amount(application),
        currency="CZK",
        recipient_name=CFG.bank.recipient_name,
        message=payment_message(application),
    )
    # generate the QR code and paste it onto a white background
    rendered = io.BytesIO()
    generator.make_image(box_size=10, border=4).save(
        rendered, output_format="png", zoom=1
    )
    rendered.seek(0)
    with Image.open(rendered) as code:
        canvas = Image.new("RGB", code.size, "white")
        canvas.paste(code, mask=code.getchannel("A"))

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()
