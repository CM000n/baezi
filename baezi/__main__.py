"""CLI für baezi."""

import sys
from pathlib import Path

import rich_click as click

from baezi.api.client import EzbookkeepingClient
from baezi.config import Config
from baezi.services.account_service import AccountService
from baezi.services.category_service import CategoryService
from baezi.services.transaction_service import TransactionImportService
from baezi.utils.logging import setup_logging

# Rich-Click Konfiguration
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True


@click.command()
@click.option(
    "--json-folder",
    "-f",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Banking4 JSON Export Ordner",
)
@click.option("--api-url", "-u", help="ezbookkeeping API URL")
@click.option("--api-token", "-t", help="API Token (alternativ: BAEZI_API_TOKEN env var)")
@click.option("--min-date", "-d", help="Mindest-Buchungsdatum (YYYY-MM-DD)")
@click.option("--dry-run", is_flag=True, help="[yellow]Testlauf ohne tatsächlichen Import[/yellow]")
@click.option("--verbose", "-v", is_flag=True, help="Debug-Ausgaben aktivieren")
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Log-Level",
)
def main(
    json_folder: Path | None,
    api_url: str | None,
    api_token: str | None,
    min_date: str | None,
    dry_run: bool,
    verbose: bool,
    log_level: str | None,
) -> None:
    """[bold green]baezi[/bold green] - Banking4 zu ezbookkeeping Importer

    Importiert Transaktionen aus Banking4 JSON-Exports in ezbookkeeping.

    [bold]Konfiguration:[/bold]

    Die Konfiguration kann über Umgebungsvariablen (.env Datei) oder
    CLI-Optionen erfolgen. CLI-Optionen überschreiben Umgebungsvariablen.

    [bold]Beispiele:[/bold]

        # Mit .env Datei
        [dim]$ baezi[/dim]

        # Mit CLI-Optionen
        [dim]$ baezi --json-folder /path/to/exports --min-date 2024-01-01[/dim]

        # Dry-Run zum Testen
        [dim]$ baezi --dry-run[/dim]
    """
    try:
        # Log-Level bestimmen
        if verbose:
            log_level = "DEBUG"
        elif not log_level:
            log_level = "INFO"

        # Logging einrichten
        setup_logging(log_level=log_level)

        # Config laden
        try:
            config = Config.from_args(
                api_url=api_url,
                api_token=api_token,
                json_folder=str(json_folder) if json_folder else None,
                min_date=min_date,
                log_level=log_level,
            )
        except ValueError as e:
            click.echo(f"❌ Konfigurationsfehler: {e}", err=True)
            click.echo(
                "\n💡 Tipp: Erstellen Sie eine .env Datei oder verwenden Sie CLI-Optionen", err=True
            )
            sys.exit(1)

        # Config validieren
        try:
            config.validate()
        except ValueError as e:
            click.echo(f"❌ Validierungsfehler: {e}", err=True)
            sys.exit(1)

        # Dry-Run Hinweis
        if dry_run:
            click.echo("🔍 DRY-RUN Modus - es werden keine Daten importiert!")
            # TODO: Dry-Run implementieren
            click.echo("⚠️  Dry-Run noch nicht implementiert")
            sys.exit(0)

        # Services initialisieren
        api_client = EzbookkeepingClient(config)

        # Health-Check
        if not api_client.health_check():
            click.echo("❌ Verbindung zu ezbookkeeping fehlgeschlagen!", err=True)
            click.echo(f"   API-URL: {config.api_base_url}", err=True)
            sys.exit(1)

        account_service = AccountService(api_client)
        category_service = CategoryService(api_client)

        # Daten laden
        account_service.load_account_map()
        category_service.load_categories()
        category_service.load_transfer_categories()

        # Import-Service
        import_service = TransactionImportService(
            api_client, config, account_service, category_service
        )

        # Import durchführen
        stats = import_service.run_import()

        # Exit-Code basierend auf Ergebnis
        if stats.errors > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\n\n⚠️  Import abgebrochen durch Benutzer", err=True)
        sys.exit(130)

    except Exception as e:
        click.echo(f"\n❌ Unerwarteter Fehler: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
