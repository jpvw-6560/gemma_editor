from dataclasses import dataclass

@dataclass(frozen=True)
class LayoutBlock:
    id: str
    x: int
    y: int
    w: int
    h: int
    text: str