import csv
import io

import yaml
from pydantic import TypeAdapter

from stezka_online_application._models import Application

YAML_KEYS = {
    "children": "deti",
    "name": "jmeno",
    "birth_date": "datum_narozeni",
    "address": "bydliste",
    "street": "ulice",
    "city": "mesto",
    "postal_code": "psc",
    "fit_for_activities": "zpusobile_akci",
    "health_details": "zdravotni_stav",
    "other_warnings": "jina_upozorneni",
    "contact": "kontakt",
    "photo_consent": "souhlas_foto",
    "guardian": "rodic",
    "person": "jmeno",
    "relation_to_child": "vztah_k_diteti",
    "phone": "telefon",
    "email": "email",
    "contacts": "dalsi_kontakty",
}


def _child(field: str) -> str:
    return f"dite_{YAML_KEYS[field]}"


def _guardian(field: str) -> str:
    return f"rodic_{YAML_KEYS[field]}"


APPLICATION_ADAPTER = TypeAdapter(Application)

CSV_COLUMNS = {
    _child("name"): lambda child, g, c: child.name,
    _child("birth_date"): lambda child, g, c: child.birth_date.isoformat(),
    _child("street"): lambda child, g, c: child.address.street,
    _child("city"): lambda child, g, c: child.address.city,
    _child("postal_code"): lambda child, g, c: child.address.postal_code,
    _child("contact"): lambda child, g, c: child.contact,
    _child("fit_for_activities"): lambda child, g, c: (
        "ano" if child.fit_for_activities else "ne"
    ),
    _child("health_details"): lambda child, g, c: child.health_details,
    _child("other_warnings"): lambda child, g, c: child.other_warnings,
    _child("photo_consent"): lambda child, g, c: "ano" if child.photo_consent else "ne",
    _guardian("person"): lambda ch, guardian, c: guardian.person,
    _guardian("relation_to_child"): lambda ch, guardian, c: guardian.relation_to_child,
    _guardian("phone"): lambda ch, guardian, c: guardian.phone,
    _guardian("email"): lambda ch, guardian, c: guardian.email,
    YAML_KEYS["contacts"]: lambda ch, g, contacts: "; ".join(
        f"{contact.person} ({contact.relation_to_child}): "
        + ", ".join(part for part in (contact.phone, contact.email) if part)
        for contact in contacts
    ),
}


def _translate(value: object) -> object:
    """Rename every key of the dumped application, at any depth."""
    if isinstance(value, dict):
        return {
            YAML_KEYS.get(key, key): _translate(item) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_translate(item) for item in value]
    return value


def to_yaml(application: Application) -> str:
    """The whole application, nested, with Czech keys."""
    return yaml.safe_dump(
        _translate(APPLICATION_ADAPTER.dump_python(application, mode="json")),
        allow_unicode=True,
        sort_keys=False,
    )


def to_csv(application: Application) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(CSV_COLUMNS), delimiter=";")
    writer.writeheader()

    # one row per child
    for child in application.children:
        writer.writerow(
            {
                column: build(child, application.guardian, application.contacts)
                for column, build in CSV_COLUMNS.items()
            }
        )

    return buffer.getvalue()
