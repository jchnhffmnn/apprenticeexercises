"""HTTP server module."""
import csv
import json

from datetime import datetime

from http_utils import TcpSocket

CRLF = "\r\n"
FILE_PATH = "film.csv"
REQUEST_TPL = "method: {}\nresource: {}\nversion: {}\nheaders: {}\nbody: {}\n"
RESPONSE_TPL = "status code: {}\nstatus msg: {}\nheaders: {}\nbody: {}\n"
STATUS_CODES = {
    200: "OK",
    404: "Not Found",
    405: "Not Allowed"
}
HTTP_RESPONSE_TPL = "{} {} {}\r\n{}\r\n\r\n{}\r\n"


def json_content(func):
    """Converts function return value to JSON."""
    def wrapper(*args, **kwargs):
        content = func(*args, **kwargs)
        if content is None:
            return (404, STATUS_CODES[404])
        return (200, json.dumps(content))
    return wrapper


class Request:
    """An HTTP Request."""

    def __init__(self, method, resource, http_version, headers, body):
        """Initializes request."""
        self.method = method
        self.resource = resource
        self.http_version = http_version
        self.headers = headers
        self.body = body

    def __repr__(self):
        """Returns request attributes formatted as a string."""
        return REQUEST_TPL.format(
            self.method,
            self.resource,
            self.http_version,
            self.headers,
            self.body
        )


class Response:
    """An HTTP Response."""

    def __init__(self, http_version, status_code, status_message, headers, body):
        """Initializes request."""
        self.http_version = http_version
        self.status_code = status_code
        self.status_message = STATUS_CODES[status_code]
        self.headers = headers
        self.body = body

    def __repr__(self):
        """Return response attributes formatted as a string."""
        return RESPONSE_TPL.format(
            self.status_code,
            self.status_message,
            self.headers,
            self.body
        )


class HTTPServer:
    """A simple HTTP server."""


    def __init__(self, host, port):
        """Initializes server."""
        self.host = host
        self.port = port
        self.socket = None
        self.collections = {
            "headers": {
                "GET": self.get_request_headers
            },
            "movies": {
                "GET": self.search_movie_title
            },
            "sort": {
                "POST": self.sort_numbers
            }
        }

    def __call__(self):
        """Starts server and execute logic."""
        with TcpSocket(self.host, self.port) as self.socket:
            while True:
                raw_request = self.recieve_request()
                request = self.process_request(raw_request)
                response = self.handle_request(request)
                data = self.send_response(response)

    def recieve_request(self):
        """Recieves raw data by client."""
        return self.socket.recieve_data()

    def process_request(self, raw_request):
        """Processes raw request to Request object."""
        request_segments = raw_request.decode().split(CRLF)
        (method, resource, http_version) = request_segments[0].split(" ")
        headers = self._get_headers(request_segments[1:-2])
        body = self._get_body(request_segments[-1])
        return Request(method, resource, http_version, headers, body)

    def handle_request(self, request):
        """Handles request and creates response instance."""
        status_code = 200
        requested_collection = request.resource.split("/")[1]
        http_method = request.method
        try:
            collection = self.collections[requested_collection]
        except KeyError:
            status_code = 404
        else:
            try:
                method = collection[http_method]
            except KeyError:
                status_code = 405
            else:
                (status_code, content) = method(request)
        if status_code != 200:
            content = STATUS_CODES[status_code]
        status_message = STATUS_CODES[status_code]
        headers = self._generate_response_headers(content)
        http_version = request.http_version
        return Response(http_version, status_code, status_message, headers, content)

    def send_response(self, response):
        """Deserializes response object and sends HTTP response to client."""
        headers = "\r\n".join(
            f"{key}: {value}" for (key, value) in response.headers.items()
        )
        response_data = HTTP_RESPONSE_TPL.format(
            response.http_version,
            response.status_code,
            response.status_message,
            headers,
            response.body
        ).encode("utf-8")
        self.socket.send_data(response_data)
        return response_data

    @staticmethod
    def _get_headers(raw_headers):
        """Puts headers inside a dict."""
        headers = {}
        for header in raw_headers:
            (key, value) = header.split(": ")
            headers[key] = value
        return headers

    @staticmethod
    def _get_body(raw_body):
        """Put JSON body inside a dict."""
        return json.loads(raw_body) if raw_body else None

    def _generate_response_headers(self, content):
        """Generates response headers."""
        return {
            "Content-Type": "application/json",
            "Host": f"{self.host}:{self.port}",
            "Date": datetime.now().ctime(),
            "Content-Length": len(content)
        }

    @staticmethod
    @json_content
    def sort_numbers(request):
        """Sorts list of numbers."""
        if not request.body:
            return []
        numbers = request.body["input"]
        return sorted(numbers)

    @staticmethod
    @json_content
    def get_request_headers(request):
        """gets headers of request."""
        return request.headers

    @staticmethod
    @json_content
    def search_movie_title(request):
        """Searches movie title."""
        movie_title = request.resource.split("/")[-1]
        with open(FILE_PATH, encoding="latin-1", newline="") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=";")
            for row in reader:
                if row["Title"] == movie_title:
                    return row
        return None


if __name__ == "__main__":
    server = HTTPServer("127.0.0.1", 7777)
    server()
