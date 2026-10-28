# INTNET-CALDAV-ICLOUD-SYNC

DESOLIC-IT PROJECT 56Q122

Bidirektionale Synchronisation von Kalendern zwischen **iCloud** und **Synology**
(CalDAV) per [`vdirsyncer`](https://vdirsyncer.pimutils.org/) – als gehärteter
Docker-Container, bedienbar rein über die Synology-Container-Manager-GUI.

> Für weitere Informationen das Dokument "DESOLIC – LEITFADEN CALDAV ICLOUD SYNCER"
> im Intranet aufrufen.

## Konfiguration

Sämtliche Einstellungen erfolgen über **Umgebungsvariablen** (GUI → Container →
Umgebung). Es ist **kein Terminal/interaktive Eingabe** nötig. Eine vollständige,
kommentierte Liste steht in [`.env.example`](.env.example).

Geheimnisse können statt als Klartext-Variable auch als Datei übergeben werden:
zu jeder Variable existiert eine `…_FILE`-Variante (z. B. `APPLE_APP_PASSWORD_FILE`),
die auf ein Docker-Secret zeigt – empfohlen.

### Kalenderauswahl (ohne Terminal)

| `COLLECTIONS_MODE` | Wann | Eintrag |
|---|---|---|
| `auto` (Default) | iCloud- und Synology-Kalender heißen gleich | nichts weiter nötig |
| `named` | nur bestimmte, gleichnamige Kalender | `COLLECTIONS="Familie,Arbeit"` |
| `mapping` | Namen unterscheiden sich | `COLLECTION_MAPPING='[["familie","ICLOUD_ID","SYNO_ID"]]'` |

Ablauf bei abweichenden Namen: Container starten → im **Log** erscheinen die
gefundenen Kalender → gewünschte Namen/IDs in die Umgebungsvariable eintragen →
Container neu starten.

## Sicherheitsmerkmale

- Läuft unprivilegiert (`PUID`/`PGID`, Privilege-Drop via `gosu`), `tini` als PID 1.
- **Kein Passwort wird in die Config geschrieben.** vdirsyncer holt die Zugangsdaten
  zur Laufzeit per `*.fetch`-Kommando (`cat`/`printenv`) direkt aus Docker-Secret
  bzw. Umgebungsvariable – weder die (ephemere, `chmod 600`) Config-Datei noch das
  Log enthalten je ein Klartext-Credential. Config-Erzeugung injection-sicher (kein `sed`/`envsubst`).
- HTTPS für die Synology-URL wird erzwungen; TLS-Verifizierung standardmäßig aktiv.
- Größenbasierte Log-Rotation; Base-Image und `vdirsyncer` sind versionsgepinnt.

Empfohlene Laufzeit-Härtung: `--read-only`, `--tmpfs /home/sync/.config`,
`--cap-drop ALL`, `--security-opt no-new-privileges:true` und Docker-Secrets.

## Build & Start

```bash
docker build -t caldav-icloud-sync:latest .

docker run -d --name caldav-sync \
  --env-file .env \
  -v /pfad/auf/synology/config:/config \
  --security-opt no-new-privileges:true \
  caldav-icloud-sync:latest
```
