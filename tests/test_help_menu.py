from app.help_menu import HelpMenu, HelpMenuDecorator, render_help_text
from app.operations import AdditionStrategy, OperationFactory


def test_help_menu_decorator_lists_word_commands_but_not_symbol_aliases():
    help_text = render_help_text()

    assert "Operations: add, subtract, multiply, divide" in help_text
    assert "int_divide, percent, abs_diff." in help_text
    assert "+" not in help_text
    assert "//" not in help_text


def test_help_menu_includes_new_factory_commands_dynamically(monkeypatch):
    strategies = dict(OperationFactory._STRATEGIES)
    strategies["new_operation"] = AdditionStrategy
    monkeypatch.setattr(OperationFactory, "_STRATEGIES", strategies)

    assert "new_operation" in render_help_text()


def test_help_menu_decorator_preserves_wrapped_menu_content():
    menu = HelpMenu()

    rendered = HelpMenuDecorator(menu).render()

    assert rendered.startswith(menu.render())
    assert "Commands: help, history" in rendered