from typing import Any, Dict

from ..services.stop_service import should_stop
from ..utils.helpers import get_state_value


class StopRequested(Exception):
    pass


async def check_stop(state: Dict[str, Any]) -> None:
    run_id = get_state_value(state, "run_id")
    if await should_stop(run_id):
        raise StopRequested()
