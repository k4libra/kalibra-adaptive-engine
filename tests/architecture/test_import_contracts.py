from importlinter.cli import lint_imports


def test_bounded_context_boundaries_hold() -> None:
    """NFR-006: no circular dependencies between bounded contexts, checked statically."""
    assert lint_imports() == 0
