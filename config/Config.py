import socket

DEFAULT_HOST_NAME = socket.gethostbyaddr(socket.gethostname())[0]
DEFAULT_PORT_NUMBER = 8001

class Config:
    """handle the optional config file"""

    def __init__(self, config_file):
        self.config = {}
        if not config_file is None:
            self.config = self.load_properties(config_file)
    
    def load_properties(self, filepath, sep='=', comment_char='#', section_char='[') -> dict:
        #credits: https://stackoverflow.com/questions/3595363/properties-file-in-python-similar-to-java-properties
        props = {}
        with open(filepath, "rt") as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith(comment_char) and not l.startswith(section_char):
                    key_value = l.split(sep)
                    key = key_value[0].strip()
                    value = sep.join(key_value[1:]).strip().strip('"') 
                    props[key] = value 
        return props

    def getServerListeningHostName(self) -> str:
        serverHostName = DEFAULT_HOST_NAME
        if 'server.listening_hostname' in self.config:
            serverHostName = self.config['server.listening_hostname']
        
        return serverHostName
    
    def getServerListeningPort(self) -> str:
        serverPort = DEFAULT_PORT_NUMBER
        if 'server.listening_port' in self.config:
            serverPort = int(self.config['server.listening_port'])
        
        return serverPort
    
    def getKeyFile(self) -> str:
        keyFile = None
        if 'server.keyfile' in self.config:
            keyFile = self.config['server.keyfile']
        
        return keyFile

    def getCertFile(self) -> str:
        certFile = None
        if 'server.certfile' in self.config:
            certFile = self.config['server.certfile']
        
        return certFile
    
    def getServerServingHostName(self) -> str:
        serverHostName = self.getServerListeningHostName()
        if 'server.serving_hostname' in self.config and self.config['server.serving_hostname'] != '':
            serverHostName = self.config['server.serving_hostname']
        
        return serverHostName
    
    def getBasicAuthCredentials(self) -> [str, str]:
        login = None
        password = None
        if "server.basicauth.login" in self.config and "server.basicauth.password" in self.config:
            login = self.config["server.basicauth.login"]
            password = self.config["server.basicauth.password"]
        
        return login, password
