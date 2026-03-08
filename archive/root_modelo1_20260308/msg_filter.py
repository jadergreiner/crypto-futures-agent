import sys

msg = sys.stdin.read()

# Remove non-ASCII characters
result = ""
for c in msg:
    if ord(c) < 128:  # Keep ASCII only
        result += c

msg = result.strip()
msg = " ".join(msg.split())  # Clean multiple spaces

sys.stdout.write(msg)
