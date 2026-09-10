import os
import tomllib
from pathlib import Path
from typing import Annotated

from pydantic import ConfigDict, Field, TypeAdapter
from pydantic.dataclasses import dataclass

CONFIG_ENV_VAR = "STEZKA_APPLICATION_CONFIG"
CONFIG_FILENAME = "config.toml"

SECTION = ConfigDict(str_strip_whitespace=False, extra="forbid")

Text = Annotated[str, Field(min_length=1)]


@dataclass(frozen=True, slots=True, config=SECTION)
class AppSection:
    title: Text
    date_format: Text
    date_mask: Text
    draft_save_interval: Annotated[int, Field(gt=0)]


@dataclass(frozen=True, slots=True, config=SECTION)
class FeeSection:
    amount: Annotated[int, Field(gt=0)]
    school_year: Text


@dataclass(frozen=True, slots=True, config=SECTION)
class BankSection:
    account: Text
    recipient_name: Text
    message_limit: Annotated[int, Field(gt=0)]


@dataclass(frozen=True, slots=True, config=SECTION)
class SmtpSection:
    host: Text
    port: Annotated[int, Field(gt=0, lt=65536)]
    sender: Text
    chief_email: Text


@dataclass(frozen=True, slots=True, config=SECTION)
class TextsSection:
    legal: Text
    intro_one_child: Text
    intro_many_children: Text
    rules_on_printed_application: Text


@dataclass(frozen=True, slots=True, config=SECTION)
class EmailSection:
    one_child_email_body: Text
    multiple_children_email_body: Text
    chief_email_body: Text


@dataclass(frozen=True, slots=True, config=SECTION)
class PdfSection:
    logo: Text
    template: Text


@dataclass(frozen=True, slots=True, config=SECTION)
class Config:
    app: AppSection
    fee: FeeSection
    bank: BankSection
    smtp: SmtpSection
    texts: TextsSection
    email: EmailSection
    pdf: PdfSection

    @property
    def legal(self) -> str:
        """The legal text, with the fee and school year substituted."""
        return self.texts.legal.format(
            school_year=self.fee.school_year, fee=self.fee.amount
        )

    @property
    def intro_one_child(self) -> str:
        return self.texts.intro_one_child.format(
            chief_email=self.smtp.chief_email, fee=self.fee.amount
        )

    @property
    def intro_many_children(self) -> str:
        return self.texts.intro_many_children.format(
            chief_email=self.smtp.chief_email, fee=self.fee.amount
        )

    @property
    def printed_rules(self) -> str:
        """The declaration above the signature lines, without the block's newlines."""
        return self.texts.rules_on_printed_application.strip()


CONFIG_ADAPTER = TypeAdapter(Config)


def config_path() -> Path:
    """Where config.toml lives: $STEZKA_APPLICATION_CONFIG, or the project root."""
    override = os.environ.get(CONFIG_ENV_VAR)
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / CONFIG_FILENAME


def load_config(path: Path | None = None) -> Config:
    """Read and validate the configuration. Raises if it is missing or wrong."""
    path = path or config_path()
    with path.open("rb") as handle:
        return CONFIG_ADAPTER.validate_python(tomllib.load(handle))


CFG = load_config()
