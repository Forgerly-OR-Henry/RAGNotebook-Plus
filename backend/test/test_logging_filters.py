import logging

from core.logging_filters import ExcludeAccessPathFilter


def _access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:59811", "GET", path, "1.1", 503),
        exc_info=None,
    )


def test_exclude_access_path_filter_drops_matching_path():
    access_filter = ExcludeAccessPathFilter(paths=["/health/ready"])

    assert not access_filter.filter(_access_record("/health/ready"))
    assert not access_filter.filter(_access_record("/health/ready?source=startup"))


def test_exclude_access_path_filter_keeps_other_paths():
    access_filter = ExcludeAccessPathFilter(paths=["/health/ready"])

    assert access_filter.filter(_access_record("/user/login/"))
