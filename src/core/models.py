from dataclasses import dataclass
from typing import Optional


@dataclass
class Chunk:
    section_no: int
    section_title: str
    content_type: str  # narrative | table | formula
    page_start: int
    page_end: int
    content: str
    paragraph_id: Optional[str] = None
    table_no: Optional[str] = None
    embedding: Optional[list[float]] = None


@dataclass
class RetrievedChunk:
    section_no: int
    section_title: str
    paragraph_id: Optional[str]
    content_type: str
    table_no: Optional[str]
    page_start: int
    page_end: int
    content: str
    score: float


@dataclass
class Variable:
    symbol: str
    name: str
    unit: str
    required: bool = True
    default: Optional[float] = None


@dataclass
class Formula:
    code: str
    title: str
    section_no: int
    expression: str
    variables: list[Variable]
    paragraph_id: Optional[str] = None
    page_no: Optional[int] = None
    result_unit: Optional[str] = None
    notes: Optional[str] = None
