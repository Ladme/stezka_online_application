import io
import unicodedata
from datetime import date

from qrplatba import QRPlatbaGenerator

from stezka_online_application._cfg import (
    BANK_ACCOUNT,
    MEMBERSHIP_FEE,
    MESSAGE_LIMIT,
    RECIPIENT_NAME,
    SCHOOL_YEAR,
)
from stezka_online_application._models import Address, Application, Child, Guardian


def _ascii(value: str) -> str:
    """Strip diacritics: the payment message may only carry plain ASCII."""
    decomposed = unicodedata.normalize("NFKD", value)
    return decomposed.encode("ascii", "ignore").decode("ascii")


def payment_message(application: Application) -> str:
    """Payment message trimmed to what the SPAYD format allows."""
    surname = application.guardian.person.split()[-1]
    names = ", ".join(child.name.split()[0] for child in application.children)
    return _ascii(f"Registrace {SCHOOL_YEAR} - {surname} - {names}")[:MESSAGE_LIMIT]


def payment_amount(application: Application) -> int:
    """One fee per registered child."""
    return MEMBERSHIP_FEE * len(application.children)


def payment_qr_code(application: Application) -> bytes:
    """The payment as a PNG QR code, for the e-mail and the confirmation dialog."""
    generator = QRPlatbaGenerator(
        BANK_ACCOUNT,
        amount=payment_amount(application),
        currency="CZK",
        recipient_name=RECIPIENT_NAME,
        message=payment_message(application),
    )
    buffer = io.BytesIO()
    generator.make_image(box_size=20, border=4).save(
        buffer, output_format="png", zoom=2
    )
    return buffer.getvalue()


if __name__ == "__main__":
    with open("qr.png", "wb") as file:
        bytes = payment_qr_code(
            Application(
                children=(
                    Child(
                        name="Jan Novák",
                        birth_date=date(2015, 12, 23),
                        address=Address(
                            "Velice dlouhý název ulice pro testování zalamování textu 134/25a",
                            "Žatec",
                            "666 66",
                        ),
                        fit_for_activities=True,
                        health_details="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                        other_warnings="Neplavec. Nemá rád výšky. Nemá rád jeskyně. Nemá rád padající listí. Nemá rád smetanu. Nemá rád, když na něj lidi mluví. Nemá rád cestování hromadnou dopravou.",
                        contact="rainbowdash6767@seznam.cz",
                        photo_consent=True,
                    ),
                    Child(
                        name="Pavlína Nováková",
                        birth_date=date(2019, 1, 4),
                        address=Address("Žitná 14", "Žatec", "666 66"),
                        fit_for_activities=True,
                        health_details="",
                        other_warnings="",
                        contact="",
                        photo_consent=False,
                    ),
                ),
                guardian=Guardian(
                    person="Jana Nováková",
                    relation_to_child="matka",
                    phone="+420 123 456 789",
                    email="jana.novakova.1987@gmail.com",
                ),
                contacts=(),
            )
        )

        file.write(bytes)
