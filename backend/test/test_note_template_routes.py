from starlette.routing import Match

from mvc.controllers.note_template_controller import note_template_router


def test_note_template_reorder_route_is_matched_before_template_id_route():
    scope = {
        "type": "http",
        "method": "PUT",
        "path": "/note-template/reorder",
        "headers": [],
        "query_string": b"",
        "root_path": "",
    }

    for route in note_template_router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            assert route.endpoint.__name__ == "reorder_templates"
            break
    else:
        raise AssertionError("PUT /note-template/reorder did not match any route")
