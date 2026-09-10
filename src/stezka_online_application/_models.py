from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    PastDate,
    TypeAdapter,
    ValidationError,
    model_validator,
)
from pydantic.dataclasses import dataclass


def is_filled(value: object, /) -> bool:
    return bool(value and str(value).strip())


def is_full_name(value: object, /) -> bool:
    """Accept only two or more words."""
    return len(str(value or "").split()) >= 2


def is_phone(value: object, /) -> bool:
    digits = re.sub(r"[\s()/.-]", "", str(value) or "")
    return re.fullmatch(r"\+?\d{9,15}", digits) is not None


def is_postal_code(value: object, /) -> bool:
    return re.fullmatch(r"\d{3} ?\d{2}", str(value or "").strip()) is not None


def require(predicate: Callable[[str], bool], expectation: str) -> AfterValidator:
    """Turn a predicate into a pydantic field validator."""

    def check(value: str) -> str:
        if not predicate(value):
            raise ValueError(f"expected {expectation}")
        return value

    return AfterValidator(check)


def optional(predicate: Callable[[Any], bool]) -> Callable[[Any], bool]:
    """Accept an empty field. Check the value only once something is typed."""

    def check(value: object, /) -> bool:
        return not is_filled(value) or predicate(value)

    return check


def czech_date_to_iso(value: object) -> object:
    """Reorder dd.mm.yyyy into the ISO order that pydantic's date parser reads."""
    if isinstance(value, str):
        parts = value.strip().split(".")
        if len(parts) == 3:
            day, month, year = (part.strip() for part in parts)
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return value


Text = Annotated[str, Field(min_length=1)]
FullName = Annotated[Text, require(is_full_name, "a first name and a surname")]
Phone = Annotated[Text, require(is_phone, "a phone number of 9 to 15 digits")]
PostalCode = Annotated[Text, require(is_postal_code, "a postal code such as 602 00")]
BirthDate = Annotated[PastDate, BeforeValidator(czech_date_to_iso)]

DATE_ADAPTER = TypeAdapter(Annotated[date, BeforeValidator(czech_date_to_iso)])
BIRTH_DATE_ADAPTER = TypeAdapter(BirthDate)

EMAIL_ADAPTER = TypeAdapter(EmailStr)


def accepts(adapter: TypeAdapter[Any], value: object) -> bool:
    """Whether a single value would pass that field's type in the model."""
    try:
        adapter.validate_python((str(value) or "").strip())
    except ValidationError:
        return False
    return True


def is_valid_date(value: object, /) -> bool:
    return accepts(DATE_ADAPTER, value)


def is_past_date(value: object, /) -> bool:
    """Whether the date is in the past."""
    return not is_valid_date(value) or accepts(BIRTH_DATE_ADAPTER, value)


def is_email(value: object, /) -> bool:
    return accepts(EMAIL_ADAPTER, value)


MODEL_CONFIG = ConfigDict(str_strip_whitespace=True, extra="forbid")


@dataclass(frozen=True, slots=True, config=MODEL_CONFIG)
class Guardian:
    """The person with parental responsibility who submits the application."""

    person: FullName
    relation_to_child: Text
    phone: Phone
    email: EmailStr


@dataclass(frozen=True, slots=True, config=MODEL_CONFIG)
class Contact:
    """Another close person, reachable by phone or e-mail (or both)."""

    person: FullName
    relation_to_child: Text
    phone: Phone | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def check_reachable(self) -> Contact:
        if self.phone is None and self.email is None:
            raise ValueError("expected a phone number or an e-mail address")
        return self


@dataclass(frozen=True, slots=True, config=MODEL_CONFIG)
class Address:
    """Residence of a child."""

    street: Text
    city: Text
    postal_code: PostalCode

    def __str__(self) -> str:
        return f"{self.street}, {self.city}, {self.postal_code}"


@dataclass(frozen=True, slots=True, config=MODEL_CONFIG)
class Child:
    """Immutable record of a child being registered."""

    name: FullName
    birth_date: BirthDate
    address: Address
    fit_for_activities: bool
    health_details: str
    other_warnings: str
    contact: str
    photo_consent: bool


@dataclass(frozen=True, slots=True, config=MODEL_CONFIG)
class Application:
    """Immutable, validated snapshot of one submitted registration form."""

    children: Annotated[tuple[Child, ...], Field(min_length=1)]
    guardian: Guardian
    contacts: tuple[Contact, ...]
