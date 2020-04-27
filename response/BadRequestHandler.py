from response.RequestHandler import RequestHandler

class BadRequestHandler(RequestHandler):
    def __init__(self, prefix, path):
        super().__init__(prefix, "", "", "", "")
        self.contents = "Unable to fetch resource:" + path
        self.contentType = 'text/plain'
        self.setStatus(404)