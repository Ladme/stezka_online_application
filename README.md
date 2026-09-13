## E-přihláška do 48. PTO Stezka

Interní aplikace [našeho oddílu](https://stezka.org/) pro online přihlašování nových členů.

### Spuštění

1. Nainstaluj [uv](https://docs.astral.sh/uv/getting-started/installation/).

2. Naklonuj tento repozitář:

```bash
git clone git@github.com:Ladme/stezka_online_application.git
```

nebo

```bash
git clone https://github.com/Ladme/stezka_online_application.git
```

3. V `config.toml` nastav účet, ze kterého se budou posílat e-maily (`smtp.sender`) a e-mail náčelníka (`smtp.chief_email`) - tam se budou posílat data z přihlášek a tam mají rodiče posílat podepsané přihlášky.

4. Vytvoř soubor `.env` a nastav v něm tyto env vars:

   - `SMTP_PASSWORD` - heslo k SMTP serveru pro účet z `smtp.sender`,
   - `STORAGE_SECRET` - tajný klíč, kterým se podepisuje session cookie. Vygeneruj ho třeba pomocí:
   - `ALTCHA_HMAC_KEY` - tajný klíč, kterým se podepisují ALTCHA výzvy (ochrana formuláře proti botům). Vygeneruj ho stejným způsobem:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

5. Spusť aplikaci:

```bash
uv run stezka-online-application
```

Aplikace poslouchá na portu `9967`. To lze změnit v `config.toml` (`app.port`).

6. Zpřístupni aplikaci uživatelům. Podle toho, kdo se k ní má dostat:

   - **Jen ty, na stejném počítači:** otevři <http://localhost:9967> v prohlížeči.
   - **Jiní lidé:** aplikaci je potřeba vystavit veřejně. Nejrychleji přes tunel, třeba [`ngrok http 9967`](https://ngrok.com/), který vypíše veřejnou adresu.
