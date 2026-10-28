"""Composable help text with operation commands supplied by the factory."""

from .operations import OperationFactory


class HelpMenu:
    """Base help-menu component for general calculator commands."""

    def render(self) -> str:
        return (
            "Commands: help, history, clear, undo, redo, save, load, exit "
            "(q also exits).\n"
            "For root, enter the radicand first and the root degree second.\n"
            "clear deletes this session's history and resets undo/redo.\n"
            "undo removes the last entry; redo restores the last undone entry.\n"
            "save writes this session; load lists earlier sessions and imports "
            "a selected entry."
        )


class HelpMenuDecorator:
    """Extend a help-menu component with the current factory operations."""

    def __init__(self, menu):
        self.menu = menu

    def render(self) -> str:
        commands = ", ".join(OperationFactory.commands())
        return f"{self.menu.render()}\nOperations: {commands}."


def render_help_text() -> str:
    """Build help at call time so newly registered operations are included."""
    return HelpMenuDecorator(HelpMenu()).render()