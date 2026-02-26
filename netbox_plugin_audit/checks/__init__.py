"""Check result types and severity levels."""

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    PASS = "pass"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class CheckResult:
    name: str
    severity: Severity
    message: str
    category: str = ""


@dataclass
class CategoryResult:
    name: str
    icon: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.severity == Severity.PASS)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if r.severity == Severity.ERROR)

    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.severity == Severity.WARNING)

    @property
    def infos(self) -> int:
        return sum(1 for r in self.results if r.severity == Severity.INFO)
