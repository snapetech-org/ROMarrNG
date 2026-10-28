import json

from romarr.app import ROMarr
from romarr.frontends import to_romarr_json
from romarr.libraries import FolderConfig, FolderLibrary


def configured_folder(tmp_path):
    root = tmp_path / "roms"
    root.mkdir()
    (root / "Final Fantasy VII.chd").write_bytes(b"disc")
    service = ROMarr({"ROMARR_DATA": str(tmp_path / "romarr.json")})
    backend = FolderLibrary(FolderConfig(root=str(root), scan_platform="psx"))
    backend.bind_catalog(service.catalog_store, "ps1", "folder-config-v1")
    service.game_libraries = [({"id": "ps1", "name": "PlayStation 1",
                                "type": "folder", "path": str(root)}, backend)]
    result = backend.scan_slice(seconds=10)
    assert result["complete"] is True
    return service, backend


def test_complete_folder_generation_exports_and_imports_metadata(tmp_path):
    service, backend = configured_folder(tmp_path)
    rows = service.frontend_rows(library_id="ps1")
    assert len(rows) == 1
    assert rows[0]["relative_path"] == "Final Fantasy VII.chd"

    payload = to_romarr_json([{
        **rows[0], "title": "Final Fantasy VII", "desc": "A role-playing game.",
        "released": "1997-01-31", "rating": 9.1, "genres": ["RPG"],
        "cover": "https://example.test/ff7.jpg", "notes": "Reviewed",
    }])
    preview = service.frontend_import_preview(
        "romarr-json", payload, library_id="ps1")
    assert preview["ok"] is True
    assert preview["matched"] == 1
    assert preview["unmatched"] == 0

    committed = service.frontend_import_commit(preview["preview_id"])
    assert committed["ok"] is True
    game = backend.games()[0]
    saved = service.store.library_metadata("ps1", game.id)
    assert saved["metadata_title"] == "Final Fantasy VII"
    assert saved["summary"] == "A role-playing game."
    assert saved["cover_url"] == "https://example.test/ff7.jpg"
    assert saved["notes"] == "Reviewed"
    assert saved["metadata_source"] == "frontend:romarr-json"


def test_frontend_preview_is_bound_to_the_complete_scan_generation(tmp_path):
    service, backend = configured_folder(tmp_path)
    game = backend.games()[0]
    service.store.set_library_metadata("ps1", game.id, {"summary": "Existing."})
    payload = json.dumps({"source": "ROMarr", "version": 1, "games": [{
        "name": game.name, "platform": "psx", "romPath": game.locator,
        "description": "Imported.",
    }]})
    preview = service.frontend_import_preview(
        "playnite", payload, library_id="ps1")
    assert preview["ok"] is True
    assert preview["value_conflicts"] == 1
    assert preview["sample"][0]["conflicts"] == ["summary"]

    backend.rescan()
    backend.scan_slice(seconds=10)
    stale = service.frontend_import_commit(preview["preview_id"])
    assert stale["ok"] is False
    assert "inventory changed" in stale["error"].lower()
