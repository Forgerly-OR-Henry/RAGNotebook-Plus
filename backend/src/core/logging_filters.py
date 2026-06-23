import logging


class MaxLevelFilter(logging.Filter):
    def __init__(self, max_level: int | str = logging.INFO):
        super().__init__()
        if isinstance(max_level, str):
            max_level = logging._nameToLevel.get(max_level.upper(), logging.INFO)
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level


class ExcludeAccessPathFilter(logging.Filter):
    def __init__(self, paths: str | list[str]):
        super().__init__()
        if isinstance(paths, str):
            paths = [paths]
        self.paths = set(paths)

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not isinstance(args, tuple) or len(args) < 3:
            return True

        full_path = str(args[2])
        path = full_path.split("?", 1)[0]
        return path not in self.paths
