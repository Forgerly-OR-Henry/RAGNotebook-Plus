import logging


class MaxLevelFilter(logging.Filter):
    def __init__(self, max_level: int | str = logging.INFO):
        super().__init__()
        if isinstance(max_level, str):
            max_level = logging._nameToLevel.get(max_level.upper(), logging.INFO)
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level
