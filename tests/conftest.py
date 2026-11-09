"""Unit tests never start unattended work or contact real account services."""
import network_guard  # installed for the entire process, including collection
import pytest


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch):
    from romarr.app import ROMarr
    original_init = ROMarr.__init__
    services = []

    def initialise(self, *args, **kwargs):
        kwargs.setdefault("start_background", False)
        original_init(self, *args, **kwargs)
        services.append(self)

    monkeypatch.setattr(ROMarr, "__init__", initialise)
    yield
    for service in reversed(services):
        service.close()
