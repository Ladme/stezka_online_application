from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from nicegui import app, binding, ui

from stezka_online_application._cfg import CFG
from stezka_online_application._models import (
    BIRTH_DATE_ADAPTER,
    Address,
    Child,
    Contact,
    is_email,
    is_filled,
    is_full_name,
    is_past_date,
    is_phone,
    is_postal_code,
    is_valid_date,
    optional,
)

Validation = dict[str, Callable[[Any], bool]]

REQUIRED: Validation = {"Vyplňte prosím toto pole.": is_filled}
REQUIRED_NAME: Validation = {
    "Vyplňte prosím toto pole.": is_filled,
    "Uveďte jméno i příjmení.": is_full_name,
}
REQUIRED_DATE: Validation = {
    "Vyplňte prosím toto pole.": is_filled,
    "Zadejte platné datum ve formátu dd.mm.rrrr.": is_valid_date,
    "Datum narození musí být v minulosti.": is_past_date,
}
REQUIRED_PHONE: Validation = {
    "Vyplňte prosím toto pole.": is_filled,
    "Zadejte telefonní číslo, např. +420 123 456 789.": is_phone,
}
REQUIRED_EMAIL: Validation = {
    "Vyplňte prosím toto pole.": is_filled,
    "Zadejte e-mail ve formátu jmeno@domena.com.": is_email,
}
REQUIRED_POSTAL: Validation = {
    "Vyplňte prosím toto pole.": is_filled,
    "Zadejte PSČ ve formátu XYZ AB, např. 602 00.": is_postal_code,
}

OPTIONAL_PHONE: Validation = {
    "Zadejte telefonní číslo, např. +420 601 123 456.": optional(is_phone),
}
OPTIONAL_EMAIL: Validation = {
    "Zadejte e-mail ve formátu jmeno@domena.cz.": optional(is_email),
}


@binding.bindable_dataclass
class ChildCount:
    """How many child blocks are on the form."""

    count: int = 1


def one_or_many(singular: str, plural: str) -> Callable[[int], str]:
    """Transformation picking the right form for a child count."""
    return lambda count: singular if count == 1 else plural


def field_label(
    text: str,
    plural: str | None = None,
    *,
    required: bool = True,
    children: ChildCount | None = None,
    gap: str = "-mb-8",
) -> None:
    """Question text placed above its input. Compulsory fields are marked with an asterisk."""
    asterisk = ' <span class="text-red-600">*</span>' if required else ""
    label = ui.html(text + asterisk).classes(
        f"text-sm text-stone-700 leading-snug {gap}"
    )
    if plural is not None and children is not None:
        label.bind_content_from(
            children, "count", one_or_many(text + asterisk, plural + asterisk)
        )


class YesNoField:
    """A boolean question answered by two mutually exclusive checkboxes."""

    def __init__(self, question: str, initial: bool | None = None) -> None:
        # guards against feedback loops between the boxes
        self._syncing = False
        field_label(question)

        with ui.row().classes("gap-6 items-center"):
            self._yes = ui.checkbox(
                "ano", value=initial is True, on_change=lambda: self._sync(self._yes)
            )
            self._no = ui.checkbox(
                "ne", value=initial is False, on_change=lambda: self._sync(self._no)
            )

        self._error = ui.label().classes("text-xs text-red-700")
        self._error.set_visibility(False)

    def _sync(self, changed: ui.checkbox) -> None:
        """Unchecking is free, checking one box clears the other one."""
        if self._syncing:
            return

        self._syncing = True

        if changed.value:
            other = self._no if changed is self._yes else self._yes
            other.value = False
            self._error.set_visibility(False)

        self._syncing = False

    @property
    def value(self) -> bool | None:
        """True for "ano", False for "ne", None while unanswered."""
        if self._yes.value:
            return True
        if self._no.value:
            return False
        return None

    def validate(self) -> bool:
        answered = self.value is not None
        self._error.text = "" if answered else "Zvolte prosím ano, nebo ne."
        self._error.set_visibility(not answered)
        return answered


T_co = TypeVar("T_co", covariant=True)


class Block(Protocol[T_co]):
    """One repeatable block: how to validate it and the value it carries."""

    def validate(self) -> bool: ...

    @property
    def value(self) -> T_co: ...

    @property
    def draft(self) -> dict[str, Any]: ...


class ContactBlock:
    """Block asking for a person and at least one way to reach them."""

    def __init__(
        self,
        on_remove: Callable[[], None],
        initial: dict[str, Any] | None = None,
    ) -> None:
        saved = initial or {}
        with ui.column().classes("w-full gap-2"):
            with ui.element("div").classes(
                "w-full grid grid-cols-1 sm:grid-cols-2 gap-2"
            ):
                self._person = ui.input(
                    "Celé jméno osoby",
                    value=saved.get("person", ""),
                    validation=REQUIRED_NAME,
                ).props("dense hide-bottom-space outlined")

                self._relation = ui.input(
                    "Vztah k dítěti (např. otec, matka)",
                    value=saved.get("relation_to_child", ""),
                    validation=REQUIRED,
                ).props("dense hide-bottom-space outlined")

                self._phone = ui.input(
                    "Telefon",
                    value=saved.get("phone", ""),
                    validation=OPTIONAL_PHONE,
                ).props("dense hide-bottom-space outlined inputmode=tel")

                self._email = ui.input(
                    "E-mail",
                    value=saved.get("email", ""),
                    validation=OPTIONAL_EMAIL,
                ).props("dense hide-bottom-space outlined inputmode=email")

            with ui.row().classes("w-full items-center no-wrap"):
                self._error = ui.label().classes("text-xs text-red-700")
                ui.button("Odebrat", on_click=on_remove).props(
                    "flat dense no-caps size=sm"
                ).classes("ml-auto")

        self._error.set_visibility(False)

    def validate(self) -> bool:
        filled_in = all(
            [
                self._person.validate(),
                self._relation.validate(),
                self._phone.validate(),
                self._email.validate(),
            ]
        )
        reachable = is_filled(self._phone.value) or is_filled(self._email.value)
        self._error.text = "" if reachable else "Uveďte telefon, e-mail, nebo obojí."
        self._error.set_visibility(not reachable)
        return filled_in and reachable

    @property
    def value(self) -> Contact:
        return Contact(
            person=self._person.value,
            relation_to_child=self._relation.value,
            phone=self._phone.value.strip() or None,
            email=self._email.value.strip() or None,
        )

    @property
    def draft(self) -> dict[str, Any]:
        """Raw input values, JSON-safe, for app.storage.user."""
        return {
            "person": self._person.value,
            "relation_to_child": self._relation.value,
            "phone": self._phone.value,
            "email": self._email.value,
        }


class ChildBlock:
    """Block collecting everything about one child."""

    def __init__(
        self,
        on_remove: Callable[[], None],
        children: ChildCount,
        initial: dict[str, Any] | None = None,
    ) -> None:
        saved = initial or {}

        with ui.column().classes("w-full gap-8"):
            heading = ui.markdown("##### Dítě").classes("text-sm text-stone-500")
            heading.bind_visibility_from(children, "count", lambda count: count > 1)

            field_label("Jméno a příjmení")
            self._name = (
                ui.input(validation=REQUIRED_NAME, value=saved.get("name", ""))
                .classes("w-full")
                .props("dense hide-bottom-space")
            )

            field_label("Datum narození")
            with (
                ui.input(
                    placeholder="dd.mm.rrrr",
                    validation=REQUIRED_DATE,
                    value=saved.get("birth_date", ""),
                )
                .classes("w-full")
                .props("dense hide-bottom-space") as birth_date
            ):
                with (
                    ui.menu().props("no-parent-event") as date_menu,
                    ui.date(mask=CFG.app.date_mask).bind_value(birth_date),
                ):
                    ui.button("Zavřít", on_click=date_menu.close).props(
                        "flat no-caps"
                    ).classes("self-end")
                with birth_date.add_slot("append"):
                    ui.icon("event").classes("cursor-pointer").on(
                        "click", date_menu.open
                    )
            self._birth_date = birth_date

            field_label("Bydliště")
            with ui.element("div").classes(
                "w-full grid grid-cols-1 sm:grid-cols-2 gap-2"
            ):
                self._street = (
                    ui.input(
                        "Ulice a číslo",
                        validation=REQUIRED,
                        value=saved.get("street", ""),
                    )
                    .props("hide-bottom-space")
                    .classes("sm:col-span-2")
                )
                self._city = ui.input(
                    "Obec", validation=REQUIRED, value=saved.get("city", "")
                ).props("hide-bottom-space")
                self._postal_code = ui.input(
                    "PSČ",
                    validation=REQUIRED_POSTAL,
                    value=saved.get("postal_code", ""),
                ).props("hide-bottom-space")

            field_label("Kontakt na dítě (nepovinné)", required=False)
            self._contact = (
                ui.input(
                    placeholder="Telefon nebo e-mail", value=saved.get("contact", "")
                )
                .classes("w-full")
                .props("dense hide-bottom-space")
            )

            self._fit = YesNoField(
                "Zdravotní stav dítěte mu umožňuje účastnit se akcí",
                initial=saved.get("fit_for_activities", None),
            )

            field_label(
                "Další informace o zdravotním stavu dítěte "
                "(např. prodělaná vážná onemocnění, alergie)",
                required=False,
            )
            self._health = (
                ui.textarea(value=saved.get("health_details", ""))
                .classes("w-full")
                .props("autogrow dense hide-bottom-space")
            )

            field_label("Jiná upozornění", required=False)
            self._warnings = (
                ui.textarea(value=saved.get("other_warnings", ""))
                .classes("w-full")
                .props("autogrow dense hide-bottom-space")
            )

            self._photo_consent = YesNoField(
                "Souhlas s pořizováním fotografií a audiovizuálních materiálů",
                initial=saved.get("photo_consent", None),
            )

            remove = (
                ui.button("Odebrat", on_click=on_remove)
                .props("flat dense no-caps size=sm")
                .classes("self-end")
            )
            remove.bind_visibility_from(children, "count", lambda count: count > 1)

    def validate(self) -> bool:
        results = [
            self._name.validate(),
            self._birth_date.validate(),
            self._street.validate(),
            self._city.validate(),
            self._postal_code.validate(),
            self._fit.validate(),
            self._photo_consent.validate(),
        ]
        return all(results)

    @property
    def value(self) -> Child:
        return Child(
            name=self._name.value,
            birth_date=BIRTH_DATE_ADAPTER.validate_python(self._birth_date.value),
            address=Address(
                street=self._street.value,
                city=self._city.value,
                postal_code=self._postal_code.value,
            ),
            fit_for_activities=bool(self._fit.value),
            health_details=self._health.value,
            other_warnings=self._warnings.value,
            contact=self._contact.value,
            photo_consent=bool(self._photo_consent.value),
        )

    @property
    def draft(self) -> dict[str, Any]:
        """Raw input values, JSON-safe, for app.storage.user."""
        return {
            "name": self._name.value,
            "birth_date": self._birth_date.value,
            "street": self._street.value,
            "city": self._city.value,
            "postal_code": self._postal_code.value,
            "contact": self._contact.value,
            "fit_for_activities": self._fit.value,
            "health_details": self._health.value,
            "other_warnings": self._warnings.value,
            "photo_consent": self._photo_consent.value,
        }


class RepeatableSection[T_co]:
    """A list of blocks that the user can extend. One block always remains."""

    def __init__(
        self,
        add_label: str,
        build_block: Callable[[Callable[[], None], dict[str, Any] | None], Block[T_co]],
        *,
        minimum: int = 1,
        on_change: Callable[[int], None] | None = None,
        draft_key: str | None = None,
    ) -> None:
        self._minimum = minimum
        self._on_change = on_change
        self._build_block = build_block
        self._draft_key = draft_key
        self._blocks: list[tuple[ui.element, Block[T_co]]] = []

        self._container = ui.column().classes("w-full gap-6 divide-y divide-stone-200")
        ui.button(add_label, icon="add", on_click=lambda: self.add_block()).props(
            "flat dense no-caps"
        ).classes("self-start")

        saved = self._saved_draft()
        for index in range(max(minimum, len(saved))):
            self.add_block(saved[index] if index < len(saved) else None)

        self._container.set_visibility(bool(self._blocks))

        if draft_key is not None:
            ui.timer(CFG.app.draft_save_interval, self.save_draft)

    def _saved_draft(self) -> list[dict[str, Any]]:
        if self._draft_key is None:
            return []

        saved = app.storage.user.get(self._draft_key)
        return saved if isinstance(saved, list) else []

    def save_draft(self) -> None:
        """Snapshot every block's raw values; called on a timer and on add/remove."""
        if self._draft_key is not None:
            app.storage.user[self._draft_key] = [
                block.draft for _, block in self._blocks
            ]

    def clear_draft(self) -> None:
        if self._draft_key is not None:
            app.storage.user.pop(self._draft_key, None)

    def add_block(self, initial: dict[str, Any] | None = None) -> None:
        with self._container, ui.element().classes("w-full") as block_ui:
            block = self._build_block(lambda: self._remove(block_ui), initial)

        self._blocks.append((block_ui, block))

        self._container.set_visibility(True)
        self.save_draft()

        if self._on_change is not None:
            self._on_change(len(self._blocks))

    def _remove(self, block_ui: ui.element) -> None:
        if len(self._blocks) <= self._minimum:
            ui.notify("Ponechte prosím alespoň jeden údaj.", type="warning")
            return

        self._container.remove(block_ui)
        self._blocks = [entry for entry in self._blocks if entry[0] is not block_ui]

        self._container.set_visibility(bool(self._blocks))
        self.save_draft()

        if self._on_change is not None:
            self._on_change(len(self._blocks))

    @property
    def values(self) -> tuple[T_co, ...]:
        return tuple(block.value for _, block in self._blocks)

    def validate(self) -> bool:
        results = [block.validate() for _, block in self._blocks]
        return all(results)


def section(
    title: str,
    plural: str | None = None,
    *,
    children: ChildCount | None = None,
) -> ui.column:
    with ui.column().classes("w-full gap-4"):
        with ui.column().classes("gap-1 w-full"):
            label = ui.label(title).classes("text-xl text-stone-900")
            if plural is not None and children is not None:
                label.bind_text_from(children, "count", one_or_many(title, plural))
            ui.element("div").classes("h-px w-12 bg-green-800")
        return ui.column().classes("w-full gap-8")
