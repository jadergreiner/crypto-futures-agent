#!/usr/bin/env python3

def filter_message(msg):
    """Remove non-ASCII characters from commit messages"""
    # Keep only ASCII characters (0-127)
    result = ''.join(c for c in msg if ord(c) < 128)
    # Clean up extra whitespace
    return ' '.join(result.split())
