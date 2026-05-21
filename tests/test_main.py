import src.main as main_module


class FakePage:
    pass


def test_main_constructs_app(monkeypatch):
    created = []

    class FakeApp:
        def __init__(self, page):
            created.append(page)

    monkeypatch.setattr(main_module, "App", FakeApp)
    page = FakePage()

    main_module.main(page)

    assert created == [page]
