import trot


def test_trot_package_is_importable() -> None:
    assert trot.__file__ is not None
