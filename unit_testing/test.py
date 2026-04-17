
from shared_code.data_handlers.read_config import get_web_host, get_allow_ping_role


def test():
    guild_id = get_allow_ping_role()
    print(guild_id)


test()