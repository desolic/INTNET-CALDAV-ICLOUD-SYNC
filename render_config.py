#!/usr/bin/env python3
"""Erzeugt die vdirsyncer-Config aus Umgebungsvariablen/Secrets.

Sicherheitsprinzip: Geheimnisse (Benutzername/Passwort) werden NICHT in die
Config geschrieben. Stattdessen holt vdirsyncer sie zur Laufzeit per
``*.fetch``-Kommando (``cat <secret-datei>`` bzw. ``printenv <VAR>``). Dadurch
steht nirgends - weder in der Config-Datei noch auf stdout/im Log - ein
Klartext-Credential. Dieses Skript liest die Geheimniswerte selbst nie ein.
"""
import json
import os
import sys
import urllib.parse


def fail(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def fetch_cmd(name: str) -> list:
    """vdirsyncer-.fetch-Kommando fuer ein Geheimnis - OHNE den Wert zu lesen.

    Bevorzugt die Datei aus NAME_FILE (Docker-Secret-Konvention), sonst die
    Umgebungsvariable NAME. Nur Pfad bzw. Variablenname (nicht der Wert) landen
    in der Config; vdirsyncer fuehrt das Kommando erst beim Sync aus.
    """
    file_path = os.environ.get(f"{name}_FILE")
    if file_path:
        if not os.path.isfile(file_path):
            fail(f"{name}_FILE verweist auf keine Datei: {file_path}")
        return ["command", "cat", file_path]
    if os.environ.get(name, "") != "":
        return ["command", "printenv", name]
    fail(f"Pflichtvariable fehlt: {name} (oder {name}_FILE)")


def value(name: str, required: bool = True) -> str:
    """Liest einen NICHT-geheimen Wert (z. B. URL) aus NAME_FILE oder NAME."""
    file_path = os.environ.get(f"{name}_FILE")
    if file_path:
        try:
            with open(file_path, encoding="utf-8") as fh:
                val = fh.read().strip()
        except OSError as exc:
            fail(f"{name}_FILE nicht lesbar: {exc}")
    else:
        val = os.environ.get(name, "")
    if required and not val:
        fail(f"Pflichtvariable fehlt: {name} (oder {name}_FILE)")
    return val


def q(val: str) -> str:
    """TOML-/JSON-sicher gequotete Zeichenkette."""
    return json.dumps(val)


def main() -> None:
    # Pflicht-Geheimnisse muessen vorhanden sein (ohne den Wert zu lesen)
    icloud_user = json.dumps(fetch_cmd("APPLE_ID"))
    icloud_pass = json.dumps(fetch_cmd("APPLE_APP_PASSWORD"))
    syno_user = json.dumps(fetch_cmd("SYNOLOGY_USER"))
    syno_pass = json.dumps(fetch_cmd("SYNOLOGY_PASSWORD"))

    # URL ist nicht geheim -> wird validiert und eingebettet
    syno_url = value("SYNOLOGY_CALDAV_URL")
    if urllib.parse.urlparse(syno_url).scheme != "https":
        fail("SYNOLOGY_CALDAV_URL muss HTTPS verwenden (Klartext-Uebertragung ist verboten).")

    conflict = os.environ.get("CONFLICT_RESOLUTION", "a wins")
    if conflict not in ("a wins", "b wins"):
        fail('CONFLICT_RESOLUTION muss "a wins" oder "b wins" sein.')

    mode = os.environ.get("COLLECTIONS_MODE", "auto")
    if mode == "auto":
        collections = '["from a", "from b"]'
    elif mode == "named":
        names = [s.strip() for s in os.environ.get("COLLECTIONS", "").split(",") if s.strip()]
        if not names:
            fail("COLLECTIONS_MODE=named, aber COLLECTIONS ist leer.")
        collections = json.dumps(names)
    elif mode == "mapping":
        raw = os.environ.get("COLLECTION_MAPPING", "").strip()
        if not raw:
            fail("COLLECTIONS_MODE=mapping, aber COLLECTION_MAPPING ist leer.")
        try:
            collections = json.dumps(json.loads(raw))
        except json.JSONDecodeError as exc:
            fail(f"COLLECTION_MAPPING ist kein gueltiges JSON: {exc}")
    else:
        fail(f"Unbekannter COLLECTIONS_MODE: {mode}")

    verify_line = ""
    if os.environ.get("SYNOLOGY_VERIFY", "true").lower() in ("false", "0", "no"):
        print(
            "⚠️  SYNOLOGY_VERIFY=false: TLS-Zertifikat wird NICHT geprueft "
            "(nur fuer vertrauenswuerdige LAN-Verbindungen mit self-signed Cert).",
            file=sys.stderr,
        )
        verify_line = "verify = false\n"

    sys.stdout.write(
        f"""[general]
status_path = "/config/status"

[pair icloud_synology]
a = "iCloud"
b = "Synology"
collections = {collections}
conflict_resolution = {q(conflict)}

[storage iCloud]
type = "caldav"
url = "https://caldav.icloud.com/"
username.fetch = {icloud_user}
password.fetch = {icloud_pass}

[storage Synology]
type = "caldav"
url = {q(syno_url)}
username.fetch = {syno_user}
password.fetch = {syno_pass}
{verify_line}"""
    )


if __name__ == "__main__":
    main()
