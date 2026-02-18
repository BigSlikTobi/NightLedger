import json
import sys
from typing import Any, BinaryIO

from nightledger_api.mcp_protocol import (
    MCPServer,
    error_response,
)


def serve_streams(*, input_stream: BinaryIO, output_stream: BinaryIO) -> None:
    server = MCPServer()
    while True:
        try:
            message = _read_framed_message(input_stream)
        except json.JSONDecodeError:
            _write_framed_message(
                output_stream,
                error_response(None, code=-32700, message="Parse error"),
            )
            continue
        except ValueError:
            _write_framed_message(
                output_stream,
                error_response(None, code=-32600, message="Invalid Request"),
            )
            continue

        if message is None:
            return

        response = server.handle_message(message)
        if response is not None:
            _write_framed_message(output_stream, response)


def _read_framed_message(input_stream: BinaryIO) -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = input_stream.readline()
        if line == b"":
            if not headers:
                return None
            raise ValueError("unexpected EOF while reading headers")
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("utf-8").strip()
        if ":" not in decoded:
            continue
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    content_length = headers.get("content-length")
    if content_length is None:
        raise ValueError("missing content-length header")

    expected_bytes = int(content_length)
    payload = input_stream.read(expected_bytes)
    if len(payload) != expected_bytes:
        raise ValueError("incomplete message body")
    decoded_payload = payload.decode("utf-8")
    parsed = json.loads(decoded_payload)
    if not isinstance(parsed, dict):
        raise ValueError("request must be a JSON object")
    return parsed


def _write_framed_message(output_stream: BinaryIO, message: dict[str, Any]) -> None:
    body = json.dumps(message, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    output_stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8"))
    output_stream.write(body)
    output_stream.flush()


def main() -> None:
    serve_streams(input_stream=sys.stdin.buffer, output_stream=sys.stdout.buffer)


if __name__ == "__main__":
    main()
