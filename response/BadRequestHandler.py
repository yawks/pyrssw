from response.RequestHandler import RequestHandler

class BadRequestHandler(RequestHandler):
    def __init__(self, path):
        super().__init__("", "", "")
        self.contents = "Unable to fetch resource:" + path
        super().setStatus(404)

    
    def getContentType(self) -> str:
        return "text/plain"
    
    def setStatus(self, status: int):
        super().setStatus(status)