import socket
from urllib.parse import urlsplit


def get_next_available_port(start: int = 10000, num: int = 1000) -> int:
    for port in range(start, start + num):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue

    raise RuntimeError("No available ports found")


def parse_host_port(url, default_scheme=None):
    """
    Parse host and port from a URL-like string.

    Parameters
    - url: a full URL like "http://localhost:10001/" or a host[:port] like "localhost:10001" or "example.com".
    - default_scheme: optional "http" or "https". If provided and the input contains no explicit port,
      the returned port will be the scheme's default (80 for http, 443 for https). If None, port stays None
      when not explicitly present.

    Returns
    - (host, port)
      - host: string (hostname or IPv6 without brackets) or None if not present
      - port: int or None

    Notes
    - This uses urlsplit and prepends '//' when the input lacks '://', so inputs like "host:port" are parsed as netloc.
    - IPv6 addresses like "[::1]:8000" are supported; returned host will be "::1".
    """
    # Ensure netloc is parsed correctly when scheme is missing by prepending '//'
    parsed = urlsplit(url if "://" in url else "//" + url)

    host = (
        parsed.hostname
    )  # hostname with IPv6 brackets removed, and username/password stripped
    port = parsed.port  # explicit port if given, else None
    scheme = parsed.scheme

    # If no explicit port and a default scheme is provided, fill default port for http/https
    if port is None:
        use_scheme = scheme or default_scheme
        if use_scheme == "http":
            port = 80
        elif use_scheme == "https":
            port = 443

    # Optional validation: ensure port number (if present) is within valid range
    if port is not None and not 1 <= port <= 65535:
        raise ValueError(f"invalid port: {port}")

    return host, port
