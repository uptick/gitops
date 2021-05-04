from typing import TypedDict


class RunOutput(TypedDict):
    exit_code: int
    output: str


class UpdateAppResult(RunOutput):
    app_name: str
