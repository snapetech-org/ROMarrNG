from romarr.app import ROMarr
from romarr.libraries import Game
from romarr.metadata import GameInfo


def configured_service(tmp_path):
    service = ROMarr({"ROMARR_DATA": str(tmp_path / "romarr.json")})
    service.store.put_item("metadata_providers", {
        "id": "rawg-test", "type": "rawg", "name": "RAWG test",
        "api_key": "configured", "enable": True,
    })
    return service


def test_manual_metadata_refresh_is_saved_and_reapplied_to_the_shelf(tmp_path):
    service = configured_service(tmp_path)
    game = Game(id="44", name="Final Fantasy VII (USA)",
                platform="Sony PlayStation", platform_slug="psx")
    service._publish_library([game], "", partial=False)
    service.metadata.identify = lambda **_kwargs: GameInfo(
        title="Final Fantasy VII", summary="A role-playing game.",
        cover_url="https://example.test/ff7.jpg", released="1997-01-31",
        rating=4.8, genres=("Role-playing (RPG)",), source="RAWG",
        matched_by="filename")

    result = service.refresh_library_metadata("default", "44")

    assert result["ok"] is True
    shelf = service.library_view().get("items", [])
    assert shelf[0]["cover"] == "https://example.test/ff7.jpg"
    assert shelf[0]["metadata_title"] == "Final Fantasy VII"
    assert shelf[0]["genres"] == ("Role-playing (RPG)",)
    assert service.store.library_metadata("default", "44")["metadata_status"] == "identified"


def test_background_enrichment_needs_a_complete_snapshot_and_respects_saved_matches(tmp_path):
    service = configured_service(tmp_path)
    game = Game(id="44", name="Final Fantasy VII (USA)",
                platform="Sony PlayStation", platform_slug="psx")
    service._publish_library([game], "", partial=True)
    calls = []
    service.metadata.identify = lambda **_kwargs: (calls.append(True) or GameInfo(
        title="Final Fantasy VII", cover_url="https://example.test/ff7.jpg",
        source="RAWG"))

    waiting = service.enrich_library_metadata()
    assert waiting["processed"] == 0
    assert calls == []

    service._publish_library([game], "", partial=False)
    completed = service.enrich_library_metadata()
    assert completed == {"processed": 1, "identified": 1,
                         "message": "identified 1 of 1 games"}
    assert len(calls) == 1

    second_pass = service.enrich_library_metadata()
    assert second_pass["processed"] == 0
    assert len(calls) == 1


def test_manual_platform_correction_is_persisted_without_moving_a_file(tmp_path):
    service = ROMarr({"ROMARR_DATA": str(tmp_path / "romarr.json")})
    game = Game(id="folder/item.iso", name="Dark Cloud",
                platform="Unknown", platform_slug="")
    service._publish_library([game], "", partial=False)

    result = service.correct_library_platform("default", "folder/item.iso", "ps2")

    assert result["ok"] is True
    row = service.library_view().get("items", [])[0]
    assert row["platform_slug"] == "ps2"
    assert row["platform"] == "Sony PlayStation 2"
    assert service.store.library_metadata("default", "folder/item.iso")[
        "platform_manual"] is True
