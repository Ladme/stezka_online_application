import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from nicegui import app, run, ui
from pydantic import ValidationError

from stezka_online_application._cfg import CFG
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
from stezka_online_application._email import send_application
from stezka_online_application._models import (
    Application,
    Child,
    Contact,
    Guardian,
)
from stezka_online_application._pdf import build_pdf
from stezka_online_application._qr import payment_amount, payment_qr_code


@ui.page("/")
def registration_page() -> None:

    def form_is_valid() -> bool:
        """Run every field's own validation and mark what needs fixing."""
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
        return all(checks)

    def collect() -> Application:
        """Freeze the answers into the model; raises ValidationError."""
        return Application(
            children=children.values,
            guardian=Guardian(
                person=guardian_name.value,
                relation_to_child=guardian_relation.value,
                phone=guardian_phone.value,
                email=guardian_email.value,
            ),
            contacts=contacts.values,
        )

    async def submit() -> None:
        """Validate, build the PDF, send both e-mails, confirm."""
        if not form_is_valid():
            ui.notify(
                "Některá pole potřebují opravu, jsou vyznačena červeně.",
                type="negative",
            )
            return

        try:
            application = collect()
        except ValidationError:
            ui.notify(
                "Přihlášku se nepodařilo zpracovat, zkuste to prosím znovu.",
                type="negative",
            )
            return

        submit_button.disable()
        progress.set_visibility(True)
        try:
            pdf = await run.io_bound(build_pdf, application)
            assert pdf is not None
            qr_code = payment_qr_code(application)
            await run.io_bound(send_application, application, pdf, qr_code)
        except Exception as e:  # noqa: BLE001
            print(e)
            ui.notify(
                "Přihlášku se nepodařilo odeslat. Zkuste to prosím znovu "
                f"nebo nám napište na {CFG.smtp.chief_email}.",
                type="negative",
                multi_line=True,
            )
            return
        finally:
            progress.set_visibility(False)
            submit_button.enable()

        show_confirmation(application, pdf, qr_code)

    def show_confirmation(application: Application, pdf: bytes, qr_code: bytes) -> None:
        """Fill the pre-built dialog with the result and open it."""
        confirmation.clear()
        with confirmation:
            ui.label("Přihláška odeslána").classes("text-lg text-stone-900")
            with ui.column().classes("gap-1"):
                for child in application.children:
                    ui.label(
                        f"{child.name}, nar. {child.birth_date.strftime(CFG.app.date_format)}"
                    ).classes("text-sm")

            ui.label(
                f"Potvrzení a PDF s přihláškou jsme poslali na "
                f"{application.guardian.email}.\nMůžete si ji taky "
                "stáhnout kliknutím na tlačítko 'Stáhnout přihlášku'."
            ).classes("text-sm text-stone-600")

            ui.button(
                "Stáhnout přihlášku",
                on_click=lambda: ui.download(pdf, "prihlaska.pdf"),
            ).props("unelevated no-caps")

            ui.separator()
            ui.label(f"Členský příspěvek: {payment_amount(application)} Kč").classes(
                "text-sm text-stone-900"
            )
            ui.image(
                "data:image/png;base64," + base64.b64encode(qr_code).decode()
            ).classes("w-48 self-center")
            ui.label("QR kód pro platbu najdete i v e-mailu.").classes(
                "text-xs text-stone-600 self-center"
            )

            ui.button("Zavřít", on_click=dialog.close).props("flat no-caps").classes(
                "self-end"
            )
        dialog.open()

    ui.page_title(CFG.app.title)
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
                ui.label(CFG.app.title).classes(
                    "serif text-3xl text-stone-900 leading-tight"
                )

            ui.html().bind_content_from(
                children_count,
                "count",
                one_or_many(
                    CFG.intro_one_child,
                    CFG.intro_many_children,
                ),
            ).classes(
                "w-full text-sm text-stone-700 leading-relaxed text-justify hyphens-auto"
            ).props("lang=cs")

        with (
            ui.card().classes("w-full p-6 shadow-none border border-stone-300"),
            section("Právní podmínky"),
        ):
            ui.markdown(CFG.legal).classes(
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
                build_block=lambda on_remove, initial: ChildBlock(
                    on_remove, children_count, initial
                ),
                on_change=lambda count: setattr(children_count, "count", count),
                draft_key="children_draft",
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
                .bind_value(app.storage.user, "guardian_name")
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
                .bind_value(app.storage.user, "guardian_relation")
            )

            field_label("Telefonní číslo", required=True)
            guardian_phone = (
                ui.input(validation=REQUIRED_PHONE)
                .classes("w-full")
                .props("dense hide-bottom-space inputmode=tel")
                .bind_value(app.storage.user, "guardian_phone_number")
            )

            field_label("E-mailová adresa", required=True)
            guardian_email = (
                ui.input(validation=REQUIRED_EMAIL)
                .classes("w-full")
                .props("dense hide-bottom-space inputmode=email")
                .bind_value(app.storage.user, "guardian_email")
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
                "Přidat další kontakt",
                ContactBlock,
                minimum=0,
                draft_key="contacts_draft",
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

        with ui.row().classes("items-center gap-3"):
            submit_button = (
                ui.button("Odeslat přihlášku", on_click=submit)
                .props("unelevated no-caps")
                .classes("px-6")
            )
            with ui.row().classes("items-center gap-2") as progress:
                ui.spinner(size="1.5rem")
                ui.label("Odesíláme přihlášku...").classes("text-sm text-stone-600")
            progress.set_visibility(False)

        with ui.dialog() as dialog, ui.card().classes("gap-3 p-6"):
            confirmation = ui.column().classes("gap-3")


def main() -> None:
    load_dotenv()

    STATIC = Path(__file__).parent / "static"
    app.add_static_files("/static", STATIC)

    ui.run(
        title=CFG.app.title,
        host="0.0.0.0",
        port=9967,
        show=False,
        reload=False,
        favicon=STATIC / "favicon.png",
        storage_secret=os.environ["STORAGE_SECRET"],
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
