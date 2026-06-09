HELP_TEXT = (
    "/mode default|fast   switch answer mode\n"
    "/source              show sources of the last answer\n"
    "/clear               clear the conversation\n"
    "/help                show this help\n"
    "/exit                quit"
)


def is_command(text: str) -> bool:
    return text.strip().startswith("/")
