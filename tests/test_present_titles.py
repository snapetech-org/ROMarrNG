"""Collections derives ownership from the complete shared library snapshot."""

from romarr.app import ROMarr
from romarr.collections import (PRESENT_UNKNOWN, PRESENT_VERIFIED,
                               PRESENT_BAD)
from romarr.libraries import Game


def service_with(tmp_path, games=None, *, partial=False, error=""):
    service = ROMarr({"ROMARR_DATA": str(tmp_path / "s.json")})
    if games is not None:
        service._publish_library(games, error, partial=partial)
    return service


def test_ownership_uses_the_complete_snapshot_beyond_the_first_page(tmp_path):
    games = [Game(id=str(n), name=f"Game {n:03d} (USA)",
                  platform="psx", platform_slug="psx")
             for n in range(180)]
    service = service_with(tmp_path, games)

    present = service._present_titles("psx")

    assert len(present) == 180
    assert "Game 179 (USA)" in present
    assert service._presence_complete is True


def test_ownership_is_scoped_to_the_selected_platform(tmp_path):
    service = service_with(tmp_path, [
        Game(id="1", name="Final Fantasy VII (USA)",
             platform="Sony PlayStation", platform_slug="psx"),
        Game(id="2", name="Final Fantasy VII (USA)",
             platform="Sony PlayStation 2", platform_slug="ps2"),
    ])

    assert set(service._present_titles("psx")) == {"Final Fantasy VII (USA)"}
    assert set(service._present_titles("ps2")) == {"Final Fantasy VII (USA)"}


def test_an_incomplete_inventory_is_unknown_not_everything_missing(tmp_path):
    service = service_with(tmp_path, [
        Game(id="1", name="Contra (USA)", platform="nes", platform_slug="nes")
    ], partial=True)

    assert service._present_titles("nes") == {}
    assert service._presence_complete is False


def test_a_failed_refresh_keeps_ownership_unknown(tmp_path):
    service = service_with(tmp_path, [
        Game(id="1", name="Contra (USA)", platform="nes", platform_slug="nes")
    ], error="library read failed")

    assert service._present_titles("nes") == {}
    assert service._presence_complete is False


def test_an_empty_complete_inventory_is_a_valid_empty_set(tmp_path):
    service = service_with(tmp_path, [])

    assert service._present_titles("nes") == {}
    assert service._presence_complete is True


def test_an_import_verdict_is_scoped_by_platform(tmp_path):
    from romarr.store import Event

    service = service_with(tmp_path, [
        Game(id="1", name="Contra (USA)", platform="nes", platform_slug="nes"),
        Game(id="2", name="Contra (USA)", platform="snes", platform_slug="snes"),
    ])
    service.store.record(Event(kind="imported", game="Contra (USA)",
                               platform="nes", detail="verified: /x/y"))

    assert service._present_titles("nes")["Contra (USA)"] == PRESENT_VERIFIED
    assert service._present_titles("snes")["Contra (USA)"] == PRESENT_UNKNOWN


def test_bad_dump_verdict_is_preserved(tmp_path):
    from romarr.store import Event

    service = service_with(tmp_path, [
        Game(id="1", name="Metroid (USA)", platform="nes", platform_slug="nes")
    ])
    service.store.record(Event(kind="imported", game="Metroid (USA)",
                               platform="nes", detail="bad-dump: /x/y"))

    assert service._present_titles("nes")["Metroid (USA)"] == PRESENT_BAD
