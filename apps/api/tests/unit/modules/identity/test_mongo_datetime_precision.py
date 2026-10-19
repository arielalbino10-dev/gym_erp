from datetime import UTC, datetime

from gym_erp_api.modules.identity.domain.time_utils import truncate_utc_to_milliseconds


def test_truncate_utc_to_milliseconds_for_bson_round_trip():
    moment = datetime(2026, 7, 1, 12, 0, 0, 123456, tzinfo=UTC)
    truncated = truncate_utc_to_milliseconds(moment)
    assert truncated.microsecond == 123000
