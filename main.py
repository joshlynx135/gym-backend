import json
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from domain.service import GymService
from domain.exceptions import NotFoundError, RuleViolationError

gym_service = GymService()

class GymHandler(BaseHTTPRequestHandler):
    
    #Helper methods
    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        json_string = json.dumps(data)
        self.wfile.write(json_string.encode('utf-8'))
        
    def _parse_url(self):
        parsed_url = urlparse(self.path)
        path_parts = [part for part in parsed_url.path.split('/') if part]
        query_params = parse_qs(parsed_url.query)
        return path_parts, query_params
    
    def _read_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body_string = self.rfile.read(content_length).decode('utf-8')
        try:
            return json.loads(body_string)
        except json.JSONDecodeError:
            raise ValueError("Malformed JSON in request body.")
    #HTTP methods

    def do_GET(self):
        parts, query = self._parse_url()
        try:
            #Route: GET /api/members
            if parts == ["api", "members"]:
                members = gym_service.list_members()
                self._send_json(200, [member.to_dict() for member in members])
            #Route: GET /api/classes
            elif parts == ["api", "classes"]:
                min_cap = query.get("min_capacity", [None])[0]
                classes = gym_service.list_classes(min_capacity=int(min_cap))
                self._send_json(200, [cls.to_dict() for cls in classes])
            else:
                self._send_json(404, {"error": "Endpoint not found."})
        except Exception as e:
            self._send_json(500, {"error": str(e)}) #Internal server error
    def do_POST(self):
        parts, _ = self._parse_url()
        
        try:
            body = self._read_body()
            #Route: POST /api/members
            if parts == ["api", "members"]:
                member = gym_service.create_member(body.get("name"), body.get("type"))
                self._send_json(201, member.to_dict())
            #Route: POST /api/classes
            elif parts == ["api", "classes"]:
                new_class = gym_service.create_class(body.get("name"), body.get("max_capacity"))
                self._send_json(201, new_class.to_dict())
            #Route: POST /api/bookings
            elif parts == ["api", "bookings"]:
                booked_class = gym_service.book_class(body.get("member_id"), body.get("class_id"))
                self._send_json(200, {"message": f"Member {body.get('member_id')} successfully booked for class {body.get('class_id')}.",
                                      "class": booked_class.to_dict()})    
            else:
                self._send_json(404, {"error": "Endpoint not found."})
        #Map domain errors to HTTP responses
        except RuleViolationError as e:
            self._send_json(409, {"error": str(e)}) #conflict
        except NotFoundError as e:
            self._send_json(404, {"error": str(e)}) #not found
        except Exception as e:
            self._send_json(400, {"error": f"An unexpected error occurred: {str(e)}"}) #bad request
    def do_PUT(self):
        parts, _ = self._parse_url()
        try:
            body = self._read_body()
            
            # Route: PUT /api/members/<id>
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "members":
                member_id = parts[2]
                updated_member = gym_service.update_member(member_id,
                                                           body.get("name"),
                                                           new_type=body.get("type"))
                self._send_json(200, updated_member.to_dict())

            # Route: PUT /api/classes/<id>
            elif len(parts) == 3 and parts[0] == "api" and parts[1] == "classes":
                class_id = parts[2]
                updated_class = gym_service.update_class(class_id, body.get("name"), body.get("max_capacity"))
                self._send_json(200, updated_class.to_dict())
            else:
                self._send_json(404, {"error": "Endpoint not found"})

        except RuleViolationError as e:
            self._send_json(409, {"error": str(e)})
        except NotFoundError as e:
            self._send_json(404, {"error": str(e)})
        except Exception as e:
            self._send_json(400, {"error": "Bad Request."})

    def do_DELETE(self):
        parts, _ = self._parse_url()
        try:
            # Route: DELETE /api/members/<id>
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "members":
                member_id = parts[2]
                gym_service.delete_member(member_id)
                self._send_json(200, {"message": "Member deleted."})

            # Route: DELETE /api/classes/<id>
            elif len(parts) == 3 and parts[0] == "api" and parts[1] == "classes":
                class_id = parts[2]
                gym_service.delete_class(class_id)
                self._send_json(200, {"message": "Class deleted."})
            else:
                self._send_json(404, {"error": "Endpoint not found"})

        except NotFoundError as e:
            self._send_json(404, {"error": str(e)})
        except Exception as e:
            self._send_json(400, {"error": "Bad Request."})

if __name__ == "__main__":
    port = 8080
    server = ThreadingHTTPServer(('localhost', port), GymHandler)
    print(f"GYM API is listening on http://localhost:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer is shutting down.")
        server.server_close()