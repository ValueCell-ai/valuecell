import socket


def get_next_available_port(start: int = 9000, num: int = 1000) -> int:
    for port in range(start, start + num):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue

    raise RuntimeError("No available ports found")
