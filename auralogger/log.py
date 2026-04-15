def log(*args, sep=" ", end="\n"):
    """Print a log message with print-compatible arguments."""
    message = sep.join(map(str, args))
    print(message, end=end)
