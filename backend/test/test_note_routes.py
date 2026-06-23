from starlette.routing import Match

from mvc.controllers.note_controller import note_router


def test_note_auto_tag_route_matches_regenerate_tags_handler():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/note/test-note-id/auto-tag",
        "headers": [],
        "query_string": b"",
        "root_path": "",
    }

    for route in note_router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            assert route.endpoint.__name__ == "regenerate_tags"
            break
    else:
        raise AssertionError("POST /note/{note_id}/auto-tag did not match any route")
