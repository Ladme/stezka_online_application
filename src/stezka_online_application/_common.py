from nicegui import ui

from stezka_online_application._cfg import DATE_FORMAT
from stezka_online_application._models import Application
from stezka_online_application._pdf import build_pdf


def handle_submission(application: Application) -> None:
    """Hand the application over to whatever should store it."""
    print(application)
    pdf = build_pdf(application)
    filename = f"prihlaska-{application.guardian.person.replace(' ', '-').lower()}.pdf"

    with ui.dialog() as dialog, ui.card().classes("gap-3 p-6"):
        ui.label("Přihláška odeslána").classes("text-lg text-stone-900")
        with ui.column().classes("gap-1"):
            for child in application.children:
                ui.label(
                    f"{child.name}, nar. {child.birth_date.strftime(DATE_FORMAT)}"
                ).classes("text-sm")
        ui.label(
            f"Potvrzení a PDF s přihláškou zašleme na {application.guardian.email}."
            "Nebo si jej můžete stáhnout stisknutím tlačítka níže."
        ).classes("text-sm text-stone-600")
        ui.button("Stáhnout PDF", on_click=lambda: ui.download(pdf, filename)).props(
            "unelevated no-caps"
        )
        ui.button("Zavřít", on_click=dialog.close).props("flat no-caps").classes(
            "self-end"
        )
    dialog.open()
