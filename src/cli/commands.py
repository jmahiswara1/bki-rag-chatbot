HELP_TEXT = (
    "/mode default|fast   switch answer mode\n"
    "/source              show sources of the last answer\n"
    "/clear               clear the conversation\n"
    "/help                show this help\n"
    "/exit                quit"
)


def is_command(text: str) -> bool:
    """Check if text starts with / (command indicator)."""
    return text.strip().startswith("/")


def parse_command(text: str) -> tuple[str, str]:
    """Parse command text into (name, arg_string).
    
    Examples:
        "/mode fast" -> ("mode", "fast")
        "/help" -> ("help", "")
        "/source" -> ("source", "")
        "/mode" -> ("mode", "")
    
    Returns:
        tuple[str, str]: (command_name_without_slash, argument_string)
    """
    text = text.strip()
    if text.startswith("/"):
        text = text[1:]  # Remove leading /
    
    parts = text.split(maxsplit=1)
    if not parts:
        return ("", "")
    
    name = parts[0].lower()
    arg_string = parts[1].strip() if len(parts) > 1 else ""
    
    return (name, arg_string)
