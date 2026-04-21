from dataclasses import dataclass, field


@dataclass
class ToolResult:
    action: str
    message: str
    appointment: dict | None = None
    suggestions: list[str] = field(default_factory=list)
    context_updates: dict | None = None
