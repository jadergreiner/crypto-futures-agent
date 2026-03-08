def filter_message(msg):
    # Remove non-ASCII characters
    result = ""
    for c in msg:
        if ord(c) < 128:  # Keep ASCII only
            result += c

    result = result.strip()
    result = " ".join(result.split())  # Clean multiple spaces

    return result
