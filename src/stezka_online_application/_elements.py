from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from nicegui import ui

from stezka_online_application._cfg import DATE_FORMAT
from stezka_online_application._models import (
    Application,
    Contact,
    is_email,
    is_filled,
    is_full_name,
    is_phone,
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
    "Zadejte datum ve formátu dd.mm.rrrr.": is_valid_date,
}
REQUIRED_PHONE: Validation = {
    "Vyplňte prosím toto pole.": is_filled,
    "Zadejte telefonní číslo, např. +420 123 456 789.": is_phone,
}
REQUIRED_EMAIL: Validation = {
    "Vyplňte prosím toto pole.": is_filled,
    "Zadejte e-mail ve formátu jmeno@domena.com.": is_email,
}

OPTIONAL_PHONE: Validation = {
    "Zadejte telefonní číslo, např. +420 601 123 456.": optional(is_phone),
}
OPTIONAL_EMAIL: Validation = {
    "Zadejte e-mail ve formátu jmeno@example.cz.": optional(is_email),
}


def field_label(text: str, *, required: bool = True, gap: str = "-mb-8") -> None:
    """Question text placed above its input. Compulsory fields are marked with an asterisk."""
    ui.html(
        f"{text}{' <span class="text-red-600">*</span>' if required else ''}"
    ).classes(f"text-sm text-stone-700 leading-snug {gap}")


class YesNoField:
    """A boolean question answered by two mutually exclusive checkboxes."""

    def __init__(self, question: str) -> None:
        # guards against feedback loops between the boxes
        self._syncing = False
        field_label(question)

        with ui.row().classes("gap-6 items-center"):
            self._yes = ui.checkbox("ano", on_change=lambda: self._sync(self._yes))
            self._no = ui.checkbox("ne", on_change=lambda: self._sync(self._no))

        self._error = ui.label().classes("text-xs text-red-700 hidden")

    def _sync(self, changed: ui.checkbox) -> None:
        """Unchecking is free, checking one box clears the other one."""
        if self._syncing:
            return

        self._syncing = True

        if changed.value:
            other = self._no if changed is self._yes else self._yes
            other.value = False
            self._error.text = ""

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
        return answered


T_co = TypeVar("T_co", covariant=True)


class Block(Protocol[T_co]):
    """One repeatable block: how to validate it and the value it carries."""

    def validate(self) -> bool: ...

    @property
    def value(self) -> T_co: ...


class ContactBlock:
    """Block asking for a person and at least one way to reach them."""

    def __init__(self, on_remove: Callable[[], None]) -> None:
        with ui.column().classes("w-full gap-2"):
            with ui.element("div").classes(
                "w-full grid grid-cols-1 sm:grid-cols-2 gap-2"
            ):
                self._person = ui.input("Celé jméno osoby", validation=REQUIRED).props(
                    "dense hide-bottom-space outlined"
                )
                self._relation = ui.input(
                    "Vztah k dítěti (např. otec, matka)", validation=REQUIRED
                ).props("dense hide-bottom-space outlined")
                self._phone = ui.input("Telefon", validation=OPTIONAL_PHONE).props(
                    "dense hide-bottom-space outlined inputmode=tel"
                )
                self._email = ui.input("E-mail", validation=OPTIONAL_EMAIL).props(
                    "dense hide-bottom-space outlined inputmode=email"
                )
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


class RepeatableSection[T_co]:
    """A list of blocks that the user can extend. One block always remains."""

    def __init__(
        self,
        add_label: str,
        build_block: Callable[[Callable[[], None]], Block[T_co]],
        *,
        minimum: int = 1,
    ) -> None:
        self._minimum = minimum
        self._build_block = build_block
        self._blocks: list[tuple[ui.element, Block[T_co]]] = []

        self._container = ui.column().classes("w-full gap-4")
        ui.button(add_label, icon="add", on_click=self.add_block).props(
            "flat dense no-caps"
        ).classes("self-start")

        for _ in range(minimum):
            self.add_block()

        self._container.set_visibility(bool(self._blocks))

    def add_block(self) -> None:
        with self._container, ui.element().classes("w-full") as block_ui:
            block = self._build_block(lambda: self._remove(block_ui))
        self._blocks.append((block_ui, block))
        self._container.set_visibility(True)

    def _remove(self, block_ui: ui.element) -> None:
        if len(self._blocks) <= self._minimum:
            ui.notify("Ponechte prosím alespoň jeden údaj.", type="warning")
            return

        self._container.remove(block_ui)
        self._blocks = [entry for entry in self._blocks if entry[0] is not block_ui]
        self._container.set_visibility(bool(self._blocks))

    @property
    def values(self) -> tuple[T_co, ...]:
        return tuple(block.value for _, block in self._blocks)

    def validate(self) -> bool:
        results = [block.validate() for _, block in self._blocks]
        return all(results)


def section(title: str) -> ui.column:
    """A titled block of questions; returns the column to fill with fields."""
    with ui.column().classes("w-full gap-4"):
        with ui.column().classes("gap-1 w-full"):
            ui.label(title).classes("text-xl text-stone-900")
            ui.element("div").classes("h-px w-12 bg-green-800")
        return ui.column().classes("w-full gap-8")


def handle_submission(application: Application) -> None:
    """Hand the immutable application over to whatever should store it.

    Replace the print with real persistence (database, CSV, e-mail, ...).
    """
    print(application)

    with ui.dialog() as dialog, ui.card().classes("gap-2 p-6"):
        ui.label("Přihláška odeslána").classes("text-lg text-stone-900")
        ui.label(
            f"Dítě: {application.child_name}, "
            f"nar. {application.birth_date.strftime(DATE_FORMAT)}"
        )
        ui.label(f"Přihlašuje: {application.guardian.person}")
        ui.label("Děkujeme, ozveme se vám na uvedené kontakty.").classes(
            "text-sm text-stone-600"
        )
        ui.button("Zavřít", on_click=dialog.close).props("flat no-caps").classes(
            "self-end"
        )
    dialog.open()
