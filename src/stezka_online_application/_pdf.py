import json
from datetime import date

import typst

from stezka_online_application._cfg import (
    DATE_FORMAT,
    RULES_ON_PRINTED_APPLICATION,
    TYPST_TEMPLATE,
)
from stezka_online_application._models import Application, Child, Contact, Guardian


def _reach(contact: Contact) -> str:
    parts = [part for part in (contact.phone, contact.email) if part]
    return " (" + ", ".join(parts) + ")" if parts else ""


def _child_data(child: Child) -> dict[str, object]:
    return {
        "name": child.name,
        "birth_date": child.birth_date.strftime(DATE_FORMAT),
        "address": child.address,
        "contact": child.contact,
        "fit_for_activities": child.fit_for_activities,
        "health_details": child.health_details,
        "other_warnings": child.other_warnings,
        "photo_consent": child.photo_consent,
    }


def build_pdf(application: Application) -> bytes:
    """Render the application: one independent, signable page per child."""
    data = {
        "children": [_child_data(child) for child in application.children],
        "guardian": {
            "person": application.guardian.person,
            "relation": application.guardian.relation_to_child,
            "phone": application.guardian.phone,
            "email": application.guardian.email,
        },
        "contacts": [
            {
                "person": contact.person,
                "relation": contact.relation_to_child,
                "reach": _reach(contact),
            }
            for contact in application.contacts
        ],
        "rules": RULES_ON_PRINTED_APPLICATION,
    }
    return typst.compile(
        TYPST_TEMPLATE.encode(),
        sys_inputs={"data": json.dumps(data, ensure_ascii=False)},
    )


if __name__ == "__main__":
    with open("output.pdf", "wb") as file:
        bytes = build_pdf(
            Application(
                children=(
                    Child(
                        name="Jan Novák",
                        birth_date=date(2015, 12, 23),
                        address="Žitná 14, Brno, 666 66",
                        fit_for_activities=True,
                        health_details="Alergie na jód.",
                        other_warnings="Neplavec. Nemá rád výšky.",
                        contact="rainbowdash6767@seznam.cz",
                        photo_consent=True,
                    ),
                    Child(
                        name="Pavlína Nováková",
                        birth_date=date(2019, 1, 4),
                        address="Žitná 14, Brno, 666 66",
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
