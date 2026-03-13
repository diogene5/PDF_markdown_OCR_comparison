from dataclasses import dataclass


STATUS_EMOJIS = {
    "success": "✅",
    "partial": "⚠️",
    "skipped": "⏭️",
    "failed": "❌",
}


@dataclass(frozen=True)
class RunResult:
    tool: str
    status: str
    message: str
    output_path: str | None = None

    def summary_line(self) -> str:
        suffix = f" [{self.output_path}]" if self.output_path else ""
        emoji = STATUS_EMOJIS.get(self.status, "•")
        return f"{emoji} {self.tool}: {self.message}{suffix}"


def combine_status(success_count: int, failure_count: int, skipped_count: int) -> str:
    if success_count and (failure_count or skipped_count):
        return "partial"
    if success_count:
        return "success"
    if failure_count:
        return "failed"
    return "skipped"
