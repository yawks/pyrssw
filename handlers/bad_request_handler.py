from handlers.request_handler import RequestHandler

class BadRequestHandler(RequestHandler):
    def __init__(self, path):
        super().__init__()
        self.contents = "Unable to fetch resource:" + path
        super().set_status(404)

    def get_content_type(self) -> str:
        return "text/plain"