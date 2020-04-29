from response.RequestHandler import RequestHandler

class BadRequestHandler(RequestHandler):
    def __init__(self, url_prefix, path):
        super().__init__(url_prefix, "", "")
        self.contents = "Unable to fetch resource:" + path
        self.contentType = 'text/plain'
        self.setStatus(404)