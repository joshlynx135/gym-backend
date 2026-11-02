import json
import socket
import sys
import traceback
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from domain.service import GymService
from domain.exceptions import NotFoundError, RuleViolationError, ValidationError

gym_service = GymService()

MAX_BODY_BYTES = 1024 * 1024  # 1 MB


class GymHandler(BaseHTTPRequestHandler):
    # Drop clients that connect and then stall (no request line, partial body, ...).
    timeout = 5

    # Helper methods
    def _send_json(self, status_code: int, data):
        payload = json.dumps(data).encode("utf-8")
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, TimeoutError, socket.timeout):
            # Client went away before we could answer
            pass

    def _parse_url(self):
        parsed_url = urlparse(self.path)
        path_parts = [part for part in parsed_url.path.split("/") if part]
        query_params = parse_qs(parsed_url.query)
        return path_parts, query_params

    def _read_body(self) -> dict:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            return {}
        try:
            content_length = int(raw_length)
        except ValueError:
            raise ValueError("Invalid Content-Length header.")

        if content_length < 0:
            raise ValueError("Content-Length cannot be negative.")
        if content_length == 0:
            return {}
        if content_length > MAX_BODY_BYTES:
            raise ValueError("Payload too large.")

        try:
            body_bytes = self.rfile.read(content_length)
            if len(body_bytes) < content_length:
                raise ValueError("Unexpected end of request body.")
            body_string = body_bytes.decode("utf-8")
        except (socket.timeout, TimeoutError):
            raise ValueError("Request timed out while reading body.")
        except UnicodeDecodeError:
            raise ValueError("Request body must be valid UTF-8.")

        try:
            data = json.loads(body_string)
        except json.JSONDecodeError:
            raise ValueError("Malformed JSON in request body.")

        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object.")
        return data

    def _dispatch(self, route):
        try:
            route()
        except (ValueError, ValidationError) as e:
            self._send_json(400, {"error": str(e)})
        except NotFoundError as e:
            self._send_json(404, {"error": str(e)})
        except RuleViolationError as e:
            self._send_json(409, {"error": str(e)})
        except (BrokenPipeError, ConnectionResetError, TimeoutError, socket.timeout):
            pass  # client dropped the connection
        except Exception:
            traceback.print_exc(file=sys.stderr)  # log details server-side only
            self._send_json(500, {"error": "Internal server error."})

    # HTTP verbs
    def do_GET(self):
        self._dispatch(self._handle_get)

    def do_POST(self):
        self._dispatch(self._handle_post)

    def do_PUT(self):
        self._dispatch(self._handle_put)

    def do_DELETE(self):
        self._dispatch(self._handle_delete)

    # Route handlers
    def _handle_get(self):
        parts, query = self._parse_url()

        # GET /api/members  or  GET /api/members?type=BASIC
        if parts == ["api", "members"]:
            member_type = query.get("type", [None])[0]
            members = gym_service.list_members(member_type=member_type)
            self._send_json(200, [m.to_dict() for m in members])

        # GET /api/members/<id>
        elif len(parts) == 3 and parts[0] == "api" and parts[1] == "members":
            member = gym_service.get_member(parts[2])
            self._send_json(200, member.to_dict())

        # GET /api/classes  or  GET /api/classes?min_capacity=10
        elif parts == ["api", "classes"]:
            min_cap_str = query.get("min_capacity", [None])[0]
            try:
                min_cap = int(min_cap_str) if min_cap_str is not None else None
            except ValueError:
                raise ValueError("Query parameter 'min_capacity' must be an integer.")
            classes = gym_service.list_classes(min_capacity=min_cap)
            self._send_json(200, [c.to_dict() for c in classes])

        # GET /api/classes/<id>
        elif len(parts) == 3 and parts[0] == "api" and parts[1] == "classes":
            workout_class = gym_service.get_class(parts[2])
            self._send_json(200, workout_class.to_dict())

        else:
            self._send_json(404, {"error": "Endpoint not found."})

    def _handle_post(self):
        parts, _ = self._parse_url()
        body = self._read_body()

        # POST /api/members
        if parts == ["api", "members"]:
            member = gym_service.create_member(body.get("name"), body.get("type"))
            self._send_json(201, member.to_dict())

        # POST /api/classes
        elif parts == ["api", "classes"]:
            new_class = gym_service.create_class(body.get("name"), body.get("max_capacity"))
            self._send_json(201, new_class.to_dict())

        # POST /api/bookings
        elif parts == ["api", "bookings"]:
            booked_class = gym_service.book_class(body.get("member_id"), body.get("class_id"))
            self._send_json(
                200,
                {
                    "message": f"Member {body.get('member_id')} successfully booked for class {body.get('class_id')}.",
                    "class": booked_class.to_dict(),
                },
            )

        else:
            self._send_json(404, {"error": "Endpoint not found."})

    def _handle_put(self):
        parts, _ = self._parse_url()
        body = self._read_body()

        # PUT /api/members/<id>
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "members":
            updated_member = gym_service.update_member(
                parts[2], new_name=body.get("name"), new_type=body.get("type")
            )
            self._send_json(200, updated_member.to_dict())

        # PUT /api/classes/<id>
        elif len(parts) == 3 and parts[0] == "api" and parts[1] == "classes":
            updated_class = gym_service.update_class(
                parts[2], new_name=body.get("name"), new_capacity=body.get("max_capacity")
            )
            self._send_json(200, updated_class.to_dict())

        else:
            self._send_json(404, {"error": "Endpoint not found."})

    def _handle_delete(self):
        parts, _ = self._parse_url()

        # DELETE /api/members/<id>
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "members":
            gym_service.delete_member(parts[2])
            self._send_json(200, {"message": "Member deleted."})

        # DELETE /api/classes/<id>
        elif len(parts) == 3 and parts[0] == "api" and parts[1] == "classes":
            gym_service.delete_class(parts[2])
            self._send_json(200, {"message": "Class deleted."})

        # DELETE /api/bookings  (body: member_id, class_id)
        elif parts == ["api", "bookings"]:
            body = self._read_body()
            updated_class = gym_service.cancel_booking(body.get("member_id"), body.get("class_id"))
            self._send_json(
                200,
                {
                    "message": "Booking cancelled.",
                    "class": updated_class.to_dict(),
                },
            )

        else:
            self._send_json(404, {"error": "Endpoint not found."})


if __name__ == "__main__":
    port = 8080
    server = ThreadingHTTPServer(("localhost", port), GymHandler)
    server.daemon_threads = True  # a stuck handler thread never blocks shutdown
    print(f"GYM API is listening on http://localhost:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer is shutting down.")
    finally:
        server.server_close()