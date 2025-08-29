def test_imports():
    import importlib

    modules = [
        "src",
        "src.data",
        "src.features",
        "src.models",
        "src.utils",
    ]

    for m in modules:
        importlib.import_module(m)

    assert True
