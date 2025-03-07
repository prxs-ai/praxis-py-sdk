from __future__ import annotfations

import re
from abc import ABC, abstractmethod
from struct import Struct
from typing import Final, cast

CAMEL_CASE_TO_SNAKE_CASE: Final[re.Pattern[str]] = re.compile(r"(?<!^)(?=[A-Z])")


def camel_case_to_snake_case(s: str) -> str:
    return CAMEL_CASE_TO_SNAKE_CASE.sub("_", s).lower()


type Username = str
type Constraint = FromUser
type Operand = Word | Hashtag | FromUser | And | Negate | MinRetweets


class QueryNode(Struct): ...


class Word(QueryNode):
    value: str


class Hashtag(QueryNode):
    value: Word


class FromUser(QueryNode):
    from_user: Username


class Filter(QueryNode):
    constraints: list[Constraint]


class Negate(QueryNode):
    operand: Operand


class And(QueryNode):
    left: Operand
    right: Operand


class MinRetweets(QueryNode):
    value: int


class MinFavorites(QueryNode):
    value: int


class MinReplies(QueryNode):
    value: int


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

    @abstractmethod
    def visit_hashtag(self, node: Hashtag) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_from_user(self, node: FromUser) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_filter(self, node: Filter) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_negate(self, node: Negate) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_and(self, node: And) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_min_retweets(self, node: MinRetweets) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_min_favorites(self, node: MinFavorites) -> R:
        raise NotImplementedError

    @abstractmethod
    def visit_min_replies(self, node: MinReplies) -> R:
        raise NotImplementedError


class QueryBuilder(Walker[str]):
    def visit_word(self, node: Word) -> str:
        return node.value

    def visit_hashtag(self, node: Hashtag) -> str:
        return "#" + self.walk(node.value)

    def visit_from_user(self, node: FromUser) -> str:
        return "from:" + node.from_user

    def visit_filter(self, node: Filter) -> str:
        return " ".join([self.walk(constr) for constr in node.constraints])

    def visit_negate(self, node: Negate) -> str:
        return "-(" + self.walk(node.operand) + ")"

    def visit_and(self, node: And) -> str:
        left = self.walk(node.left)
        right = self.walk(node.right)

        return f"({left}) AND ({right})"

    def visit_min_retweets(self, node: MinRetweets) -> str:
        return "min_retweets:" + str(node.value)

    def visit_min_favorites(self, node: MinFavorites) -> str:
        return "min_faves:" + str(node.value)

    def visit_min_replies(self, node: MinReplies) -> str:
        return "min_replies:" + str(node.value)


def build_query(ast: QueryNode) -> str:
    return QueryBuilder().walk(ast)
