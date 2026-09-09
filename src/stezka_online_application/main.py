from pathlib import Path

from nicegui import app, ui
from pydantic import ValidationError

from stezka_online_application._cfg import (
    APP_TITLE,
    INTRO_MANY,
    INTRO_ONE,
    RULES,
)
from stezka_online_application._common import handle_submission
from stezka_online_application._elements import (
    REQUIRED,
    REQUIRED_EMAIL,
    REQUIRED_NAME,
    REQUIRED_PHONE,
    ChildBlock,
    ChildCount,
    ContactBlock,
    RepeatableSection,
    field_label,
    one_or_many,
    section,
)
from stezka_online_application._models import (
    Application,
    Child,
    Contact,
    Guardian,
)


@ui.page("/")
def registration_page() -> None:
    ui.page_title(APP_TITLE)
    ui.colors(primary="#2f6b3f")
    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600'
        '&family=Source+Sans+3:wght@400;500&display=swap" rel="stylesheet">'
        '<style>body{font-family:"Source Sans 3",sans-serif}'
        '.serif{font-family:"Source Serif 4",serif}</style>'
    )
    ui.query("body").classes("bg-stone-100")

    children_count = ChildCount()

    with ui.column().classes("w-full max-w-2xl mx-auto p-4 md:p-8 gap-6"):
        with ui.column().classes("gap-1"):
            with ui.row().classes("w-full items-center gap-4 no-wrap"):
                ui.image("/static/logo.png").classes("w-16 shrink-0")
                ui.label(APP_TITLE).classes(
                    "serif text-3xl text-stone-900 leading-tight"
                )

            ui.html().bind_content_from(
                children_count, "count", one_or_many(INTRO_ONE, INTRO_MANY)
            ).classes(
                "w-full text-sm text-stone-700 leading-relaxed text-justify hyphens-auto"
            ).props("lang=cs")

        with (
            ui.card().classes("w-full p-6 shadow-none border border-stone-300"),
            section("Právní podmínky"),
        ):
            ui.markdown(RULES).classes(
                "w-full pr-4 text-sm text-stone-700 leading-relaxed text-justify hyphens-auto"
            ).props("lang=cs")

        with (
            ui.card().classes("w-full p-6 shadow-none border border-stone-300"),
            section(
                "Informace o dítěti", "Informace o dětech", children=children_count
            ),
        ):
            children: RepeatableSection[Child] = RepeatableSection(
                "Přidat další dítě",
                build_block=lambda on_remove: ChildBlock(on_remove, children_count),
                on_change=lambda count: setattr(children_count, "count", count),
            )

        with (
            ui.card().classes("w-full p-6 shadow-none border border-stone-300"),
            section("Osoba vykonávající rodičovskou odpovědnost"),
        ):
            ui.label().bind_text_from(
                children_count,
                "count",
                one_or_many(
                    "Osoba oprávněná přihlásit dítě do oddílu. "
                    "Potřebujeme na ni telefon i e-mail.",
                    "Osoba oprávněná přihlásit děti do oddílu. "
                    "Potřebujeme na ni telefon i e-mail.",
                ),
            ).classes("w-full text-sm text-stone-600")

            field_label("Jméno a příjmení")
            guardian_name = (
                ui.input(validation=REQUIRED_NAME)
                .classes("w-full")
                .props("dense hide-bottom-space")
            )

            field_label(
                "Vztah k dítěti (např. otec, matka)",
                "Vztah k dětem (např. otec, matka)",
                children=children_count,
            )
            guardian_relation = (
                ui.input(validation=REQUIRED)
                .classes("w-full")
                .props("dense hide-bottom-space")
            )

            field_label("Telefonní číslo", required=True)
            guardian_phone = (
                ui.input(validation=REQUIRED_PHONE)
                .classes("w-full")
                .props("dense hide-bottom-space inputmode=tel")
            )

            field_label("E-mailová adresa", required=True)
            guardian_email = (
                ui.input(validation=REQUIRED_EMAIL)
                .classes("w-full")
                .props("dense hide-bottom-space inputmode=tel")
            )

        with (
            ui.card().classes("w-full p-6 shadow-none border border-stone-300"),
            section("Další kontakty"),
        ):
            ui.label(
                "Nepovinné. Můžete uvést další osoby, které máme v případě "
                "potřeby kontaktovat. U každé stačí telefon nebo e-mail."
            ).classes("w-full text-sm text-stone-600")

            contacts: RepeatableSection[Contact] = RepeatableSection(
                "Přidat další kontakt", ContactBlock, minimum=0
            )

        with ui.card().classes("w-full p-6 shadow-none border border-stone-300"):
            rules_accepted = ui.checkbox(
                "Potvrzuji, že jsem se seznámil(a) s výše uvedenými podmínkami a souhlasím s nimi"
            )
            rules_error = ui.label(
                "Bez souhlasu s podmínkami nelze přihlášku odeslat."
            ).classes("text-xs text-red-700")
            rules_error.set_visibility(False)

        rules_accepted.on_value_change(
            lambda: rules_error.set_visibility(not rules_accepted.value)
        )

        def submit() -> None:
            """Validate everything and save the answers into a dataclass."""
            rules_error.set_visibility(not rules_accepted.value)
            checks = [
                children.validate(),
                guardian_name.validate(),
                guardian_relation.validate(),
                guardian_phone.validate(),
                guardian_email.validate(),
                contacts.validate(),
                rules_accepted.value,
            ]
            if not all(checks):
                ui.notify(
                    "Některá pole potřebují opravu, jsou vyznačena červeně.",
                    type="negative",
                )
                return

            try:
                application = Application(
                    children=children.values,
                    guardian=Guardian(
                        person=guardian_name.value,
                        relation_to_child=guardian_relation.value,
                        phone=guardian_phone.value,
                        email=guardian_email.value,
                    ),
                    contacts=contacts.values,
                )
            except ValidationError as error:
                print(error)
                ui.notify(
                    "Přihlášku se nepodařilo zpracovat, zkuste to prosím znovu.",
                    type="negative",
                )
                return

            handle_submission(application)

        ui.button("Odeslat přihlášku", on_click=submit).props(
            "unelevated no-caps"
        ).classes("self-start px-6")


def main() -> None:
    STATIC = Path(__file__).parent / "static"
    app.add_static_files("/static", STATIC)

    ui.run(title=APP_TITLE, reload=False, favicon=STATIC / "favicon.png")


if __name__ in {"__main__", "__mp_main__"}:
    main()
