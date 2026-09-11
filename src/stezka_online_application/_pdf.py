import json
from datetime import date

import typst

from stezka_online_application._cfg import CFG
from stezka_online_application._models import (
    Address,
    Application,
    Child,
    Contact,
    Guardian,
)

CZECH_MONTHS = (
    "ledna",
    "února",
    "března",
    "dubna",
    "května",
    "června",
    "července",
    "srpna",
    "září",
    "října",
    "listopadu",
    "prosince",
)


def czech_date(value: date) -> str:
    """Czech long date, e.g. '3. května 2015'."""
    return f"{value.day}. {CZECH_MONTHS[value.month - 1]} {value.year}"


def _reach(contact: Contact) -> str:
    parts = [part for part in (contact.phone, contact.email) if part]
    return " (" + ", ".join(parts) + ")" if parts else ""


def _child_data(child: Child) -> dict[str, object]:
    return {
        "name": child.name,
        "birth_date": czech_date(child.birth_date),
        "address": str(child.address),
        "city": child.address.city,
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
        "rules": CFG.printed_rules,
        "date": czech_date(date.today()),  # noqa: DTZ011
        "logo": CFG.pdf.logo,
    }

    return typst.compile(
        CFG.pdf.template.encode(),
        sys_inputs={"data": json.dumps(data, ensure_ascii=False)},
    )


# test building PDF
if __name__ == "__main__":
    with open("output.pdf", "wb") as file:
        bytes = build_pdf(
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
