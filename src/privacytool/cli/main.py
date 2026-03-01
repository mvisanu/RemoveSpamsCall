"""CLI entry point — registers all sub-commands."""

from __future__ import annotations

import typer

from privacytool.core.config import load_env
from privacytool.core.logger import configure_root_logger

app = typer.Typer(
    name="privacytool",
    help="Personal data removal and privacy protection CLI.",
    no_args_is_help=True,
)

# Import and register sub-commands
from privacytool.cli.cmd_init import init_cmd  # noqa: E402
from privacytool.cli.cmd_config import config_app  # noqa: E402
from privacytool.cli.cmd_scan import scan_cmd  # noqa: E402
from privacytool.cli.cmd_review import review_cmd  # noqa: E402
from privacytool.cli.cmd_act import act_cmd  # noqa: E402
from privacytool.cli.cmd_status import status_cmd  # noqa: E402
from privacytool.cli.cmd_resolve import resolve_cmd  # noqa: E402
from privacytool.cli.cmd_followups import followups_cmd  # noqa: E402
from privacytool.cli.cmd_export import export_cmd  # noqa: E402

app.command("init")(init_cmd)
app.add_typer(config_app, name="config")
app.command("scan")(scan_cmd)
app.command("review")(review_cmd)
app.command("act")(act_cmd)
app.command("status")(status_cmd)
app.command("resolve")(resolve_cmd)
app.command("followups")(followups_cmd)
app.command("export")(export_cmd)


@app.callback()
def main_callback(
    log_level: str = typer.Option("INFO", "--log-level", envvar="LOG_LEVEL"),
) -> None:
    """Global startup — load environment and configure logging."""
    load_env()
    configure_root_logger(log_level)


if __name__ == "__main__":
    app()
