from __future__ import annotfations

import re
from abc import ABC, abstractmethod
from struct import Struct
from typing import Final, cast

CAMEL_CASE_TO_SNAKE_CASE: Final[re.Pattern[str]] = re.compile(r"(?<!^)(?=[A-Z])")


def camel_case_to_snake_case(s: str) -> str:
    return CAMEL_CASE_TO_SNAKE_CASE.sub("_", s).lower()


class QueryNode(Struct): ...


class Word(QueryNode):
    value: str


class Walker[R](ABC):
    __slots__ = ()

    def walk(self, node: QueryNode) -> R:
        name = camel_case_to_snake_case("visit_" + type(node).__name__)
        method = getattr(self, name, None)
        if method is None:
            raise RuntimeError(f"No implementation found for node: {node}")

        return cast(R, method(node))

    @abstractmethod
    def visit_word(self, node: Word) -> R:
        raise NotImplementedError


class QueryBuilder(Walker[str]):
    def visit_word(self, node: Word) -> str:
        return node.value


def build_query(ast: QueryNode) -> str:
    return QueryBuilder().walk(ast)
