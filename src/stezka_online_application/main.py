from nicegui import ui
from pydantic import ValidationError

from stezka_online_application._cfg import APP_TITLE, DATE_MASK, INTRO, RULES
from stezka_online_application._elements import (
    REQUIRED,
    REQUIRED_DATE,
    REQUIRED_NAME,
    ContactBlock,
    RepeatableSection,
    YesNoField,
    field_label,
    handle_submission,
    section,
)
from stezka_online_application._models import BIRTH_DATE_ADAPTER, Application, Contact


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

    with ui.column().classes("w-full max-w-2xl mx-auto p-4 md:p-8 gap-6"):
        with ui.column().classes("gap-1"):
            ui.label(APP_TITLE).classes("serif text-3xl text-stone-900 leading-tight")
            ui.html(INTRO).classes("w-full text-sm text-stone-700 leading-relaxed")

        with (
            ui.card().classes("w-full p-6 shadow-none border border-stone-300"),
            section("Právní podmínky"),
        ):
            ui.markdown(RULES).classes("w-full text-sm leading-relaxed")

        with (
            ui.card().classes("w-full p-6 shadow-none border border-stone-300"),
            section("Informace o dítěti"),
        ):
            field_label("Jméno a příjmení")
            child_name = (
                ui.input(validation=REQUIRED_NAME)
                .classes("w-full")
                .props("dense hide-bottom-space")
            )

            field_label("Datum narození")
            with (
                ui.input(placeholder="dd.mm.rrrr", validation=REQUIRED_DATE)
                .classes("w-full")
                .props("dense hide-bottom-space") as birth_date
            ):
                with (
                    ui.menu().props("no-parent-event") as date_menu,
                    ui.date(mask=DATE_MASK).bind_value(birth_date),
                ):
                    ui.button("Zavřít", on_click=date_menu.close).props(
                        "flat no-caps"
                    ).classes("self-end")
                with birth_date.add_slot("append"):
                    ui.icon("event").classes("cursor-pointer").on(
                        "click", date_menu.open
                    )

            field_label("Bydliště")
            address = (
                ui.input(placeholder="Ulice a číslo, město, PSČ", validation=REQUIRED)
                .classes("w-full")
                .props("dense hide-bottom-space")
            )

            fit_for_activities = YesNoField(
                "Zdravotní stav dítěte mu umožňuje účastnit se akcí"
            )

            field_label(
                "Další informace o zdravotním stavu dítěte (např. prodělaná vážná onemocnění, alergie)",
                required=False,
            )
            health_details = (
                ui.textarea()
                .classes("w-full")
                .props("autogrow dense hide-bottom-space")
            )

            field_label("Jiná upozornění", required=False)
            other_warnings = (
                ui.textarea()
                .classes("w-full")
                .props("autogrow dense hide-bottom-space")
            )

            field_label("Kontakt na dítě", required=False)
            child_contact = (
                ui.input(placeholder="Telefon nebo e-mail")
                .classes("w-full")
                .props("dense hide-bottom-space")
            )

            photo_consent = YesNoField(
                "Souhlas s pořizováním fotografií a audiovizuálních materiálů"
            )

        with (
            ui.card().classes("w-full p-6 shadow-none border border-stone-300"),
            section("Kontakt na rodiče či jiné blízké osoby"),
        ):
            field_label(
                "Celé jméno osoby vykonávající rodičovskou odpovědnost "
                "oprávněné přihlásit dítě do oddílu"
            )
            guardian_name = (
                ui.input(validation=REQUIRED_NAME)
                .classes("w-full")
                .props("dense hide-bottom-space")
            )

            field_label("Kontakty na rodiče či jiné blízké osoby")
            contacts: RepeatableSection[Contact] = RepeatableSection(
                "Přidat další kontakt", ContactBlock
            )

        with ui.card().classes("w-full p-6 shadow-none border border-stone-300"):
            rules_accepted = ui.checkbox(
                "Potvrzuji, že jsem se seznámil(a) s výše uvedenými podmínkami a souhlasím s nimi"
            )
            rules_error = ui.label(
                "Bez souhlasu s pravidly nelze přihlášku odeslat."
            ).classes("text-xs text-red-700")
            rules_error.set_visibility(False)

        rules_accepted.on_value_change(
            lambda: rules_error.set_visibility(not rules_accepted.value)
        )

        def submit() -> None:
            """Validate everything and save the answers into a dataclass."""
            checks = [
                child_name.validate(),
                birth_date.validate(),
                address.validate(),
                fit_for_activities.validate(),
                photo_consent.validate(),
                guardian_name.validate(),
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
                    child_name=child_name.value,
                    birth_date=BIRTH_DATE_ADAPTER.validate_python(birth_date.value),
                    address=address.value,
                    fit_for_activities=bool(fit_for_activities.value),
                    health_details=health_details.value,
                    other_warnings=other_warnings.value,
                    child_contact=child_contact.value,
                    photo_consent=bool(photo_consent.value),
                    guardian_name=guardian_name.value,
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
    ui.run(title=APP_TITLE, reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    main()
