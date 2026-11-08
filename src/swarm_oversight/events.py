"""Request records. Visible fields go to the overseer; hidden labels are stored separately."""
from pydantic import BaseModel, Field


class Event(BaseModel):
    request_id: str
    root_id: str
    request_text: str
    tool: str
    args: dict = Field(default_factory=dict)
    paths_read: list[str] = Field(default_factory=list)
    paths_written: list[str] = Field(default_factory=list)
    seq: int = 0                     # order within its episode
    stream_position: int | None = None  # set when episodes are merged into a stream
    timestamp: float = 0.0
    claimed_name: str | None = None
    verdict: str | None = None
    score: float | None = None
    ok: bool | None = None
    result_preview: str | None = None


class HiddenLabels(BaseModel):
    request_id: str
    episode_id: str
    is_attack: bool
    piece_index: int | None = None
    task_id: str | None = None
    family: str | None = None
    attack: str | None = None


VISIBLE_FIELDS = ["request_id", "root_id", "request_text", "tool", "paths_read", "paths_written",
                  "stream_position"]
