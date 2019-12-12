from __future__ import annotations

import dataclasses
import itertools
import typing

import click

from .record import Record
from .text import format_multiline

Level = typing.Optional[str]


@dataclasses.dataclass()
class Color:
    fg: typing.Optional[str] = None

    def style(self, text: str) -> str:
        return click.style(text, fg=self.fg)


COLORS: typing.Mapping[str, Color] = {
    "INFO".casefold(): Color(fg="cyan"),
    "WARNING".casefold(): Color(fg="yellow"),
    "WARN".casefold(): Color(fg="yellow"),
    "ERROR".casefold(): Color(fg="red"),
    "CRITICAL".casefold(): Color(fg="red"),
}


def template_from_keys(*keys: str) -> str:
    return " ".join(
        f"{click.style(f'{k}=', fg='white')}{{__json__[{k}]}}" for k in keys
    )


@dataclasses.dataclass()
class Pattern:
    level_key: typing.Optional[str] = "level"
    multiline_keys: typing.Sequence[str] = ()

    def format_record(self, record: Record) -> str:
        message = self.format_message(record)

        # We add extra whitespace to a record if it has multiline strings.
        blocks: typing.Tuple[str, ...] = tuple(self.format_multiline(record))
        if blocks:
            lines = "\n\n".join(blocks)
            return f"{message}\n\n{lines}\n"

        return message

    def format_message(self, record: Record) -> str:
        raise NotImplementedError

    def format_multiline(self, record: Record) -> typing.Iterator[str]:
        for key in self.multiline_keys:
            value = record.extract(key)
            if value:
                string = record.value_to_string(value)
                yield format_multiline(string, dim=True)

    def highlight_color(self, record: Record) -> Color:
        level: Level = record.extract(self.level_key)
        color: Color = COLORS.get(level.casefold(), Color())
        return color

    def replace(self, **changes: typing.Any) -> Pattern:
        changes = {k: v for k, v in changes.items() if v}
        return dataclasses.replace(self, **changes)

    def add_multiline_keys(
        self, multiline_keys: typing.Sequence[str], reset_multiline_keys: bool = False
    ) -> Pattern:
        if not reset_multiline_keys:
            multiline_keys = list(itertools.chain(self.multiline_keys, multiline_keys))
        return dataclasses.replace(self, multiline_keys=multiline_keys)


@dataclasses.dataclass()
class TemplatePattern(Pattern):
    template: str = "{{__message__}}"

    def format_message(self, record: Record) -> str:
        return self.highlight_color(record).style(self.template.format_map(record.json))


@dataclasses.dataclass()
class KeyValuePattern(Pattern):
    keys: typing.Sequence[str] = ("__message__",)

    def format_message(self, record: Record) -> str:
        return " ".join(self.format_pair(record, key) for key in self.keys)

    def format_pair(self, record: Record, key: str) -> str:
        k_color = Color(fg="white")
        v_color = self.highlight_color(record)
        k = k_color.style(self.format_key(key))
        v = v_color.style(self.format_value(record.extract(key)))
        return f"{k}{v}"

    @staticmethod
    def format_key(key: str) -> str:
        return f"{key}="

    @staticmethod
    def format_value(value: str) -> str:
        return f'"{value}"'
