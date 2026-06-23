"""Top-level CLI for agent-ci-kit.

Mounts each bundled tool as a subcommand group. The click-based tools are mounted
directly; patch-context uses argparse, so it is wrapped as a passthrough command.
"""

from __future__ import annotations

import click

from agentci import __version__
from agentci.cirepro.cli import main as cirepro_cli
from agentci.mcpgate.cli import cli as mcpgate_cli
from agentci.mcpreplay.cli import main as mcpreplay_cli
from agentci.patchcontext import cli as patchcontext_module
from agentci.toolfence.cli import main as toolfence_cli


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="agentci")
def main() -> None:
    """CI-grade evidence and safety tools for AI agents, MCP servers, and OSS work.

    \b
    ci-repro       Turn CI failure logs into local repro plans and PR evidence.
    patch-context  Build issue-specific context packs for coding agents.
    mcp-gate       CI gate for MCP servers (handshake, tools, secret scan).
    mcp-replay     Record and replay MCP JSON-RPC traffic as reviewable fixtures.
    tool-fence     Deterministic safety regression tests for agent tool calls.
    """


main.add_command(cirepro_cli, name="ci-repro")
main.add_command(mcpreplay_cli, name="mcp-replay")
main.add_command(toolfence_cli, name="tool-fence")
main.add_command(mcpgate_cli, name="mcp-gate")


@main.command(
    "patch-context",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    add_help_option=False,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def patch_context(args: tuple[str, ...]) -> None:
    """Build issue-specific context packs for coding agents.

    Forwards all arguments to the patch-context CLI, e.g.:
    `agentci patch-context scan --repo . --issue issue.md`.
    """
    raise SystemExit(patchcontext_module.main(list(args)))


if __name__ == "__main__":
    main()
