from dataclasses import dataclass

@dataclass(frozen=True)
class StateBlock:
    code: str
    label: str
    x: int
    y: int
    w: int
    h: int
    
