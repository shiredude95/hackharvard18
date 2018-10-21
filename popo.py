# This code parses date/times, so please
#
#     pip install python-dateutil
#
# To use this code, make sure you
#
#     import json
#
# and then, to convert JSON from a string, do
#
#     result = welcome_from_dict(json.loads(json_string))

from typing import Any, List, TypeVar, Callable, Type, cast
from datetime import datetime
import dateutil.parser


T = TypeVar("T")


def from_str(x: Any) -> str:
    # assert isinstance(x, str)
    return x


def from_datetime(x: Any) -> datetime:
    return dateutil.parser.parse(x)


def from_int(x: Any) -> int:
    return x


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    # assert isinstance(x, list)
    return [f(y) for y in x]


def to_class(c: Type[T], x: Any) -> dict:
    # assert isinstance(x, c)
    return cast(Any, x).to_dict()


class QA:
    id: str
    question: str
    answer: str

    def __init__(self, id: str, question: str, answer: str) -> None:
        self.id = id
        self.question = question
        self.answer = answer

    @staticmethod
    def from_dict(obj: Any) -> 'QA':
        # assert isinstance(obj, dict)
        id = from_str(obj.get("_id"))
        question = from_str(obj.get("question"))
        answer = from_str(obj.get("answer"))
        return QA(id, question, answer)

    def to_dict(self) -> dict:
        result: dict = {}
        result["_id"] = from_str(self.id)
        result["question"] = from_str(self.question)
        result["answer"] = from_str(self.answer)
        return result


class Review:
    id: str
    date_of_review: datetime
    score: int

    def __init__(self, id: str, date_of_review: datetime, score: int) -> None:
        self.id = id
        self.date_of_review = date_of_review
        self.score = score

    @staticmethod
    def from_dict(obj: Any) -> 'Review':
        # assert isinstance(obj, dict)
        id = from_str(obj.get("_id"))
        date_of_review = from_datetime(obj.get("dateOfReview"))
        score = from_int(obj.get("score"))
        return Review(id, date_of_review, score)

    def to_dict(self) -> dict:
        result: dict = {}
        result["_id"] = from_str(self.id)
        result["dateOfReview"] = self.date_of_review.isoformat()
        result["score"] = from_int(self.score)
        return result


class WelcomeElement:
    threshold: int
    id: str
    qa: List[QA]
    name: str
    retainability: int
    reviews: List[Review]
    strength: int
    priority: int
    created_at: datetime
    updated_at: datetime
    v: int

    def __init__(self, threshold: int, id: str, qa: List[QA], name: str, retainability: int, reviews: List[Review], strength: int, priority: int, created_at: datetime, updated_at: datetime, v: int) -> None:
        self.threshold = threshold
        self.id = id
        self.qa = qa
        self.name = name
        self.retainability = retainability
        self.reviews = reviews
        self.strength = strength
        self.priority = priority
        self.created_at = created_at
        self.updated_at = updated_at
        self.v = v

    @staticmethod
    def from_dict(obj: Any) -> 'WelcomeElement':
        # assert isinstance(obj, dict)
        threshold = from_int(obj.get("threshold"))
        id = from_str(obj.get("_id"))
        qa = from_list(QA.from_dict, obj.get("qa"))
        name = from_str(obj.get("name"))
        retainability = from_int(obj.get("retainability"))
        reviews = from_list(Review.from_dict, obj.get("reviews"))
        strength = from_int(obj.get("strength"))
        priority = int(from_str(obj.get("priority")))
        created_at = from_datetime(obj.get("createdAt"))
        updated_at = from_datetime(obj.get("updatedAt"))
        v = from_int(obj.get("__v"))
        return WelcomeElement(threshold, id, qa, name, retainability, reviews, strength, priority, created_at, updated_at, v)

    def to_dict(self) -> dict:
        result: dict = {}
        result["threshold"] = from_int(self.threshold)
        result["_id"] = from_str(self.id)
        result["qa"] = from_list(lambda x: to_class(QA, x), self.qa)
        result["name"] = from_str(self.name)
        result["retainability"] = from_int(self.retainability)
        result["reviews"] = from_list(lambda x: to_class(Review, x), self.reviews)
        result["strength"] = from_int(self.strength)
        result["priority"] = from_str(str(self.priority))
        result["createdAt"] = self.created_at.isoformat()
        result["updatedAt"] = self.updated_at.isoformat()
        result["__v"] = from_int(self.v)
        return result


def welcome_from_dict(s: Any) -> List[WelcomeElement]:
    return from_list(WelcomeElement.from_dict, s)


def welcome_to_dict(x: List[WelcomeElement]) -> Any:
    return from_list(lambda x: to_class(WelcomeElement, x), x)
