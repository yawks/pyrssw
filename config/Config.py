import socket

DEFAULT_HOST_NAME = socket.gethostbyaddr(socket.gethostname())[0]
DEFAULT_PORT_NUMBER = 8001

#handle the optional config file
class Config:

    def __init__(self, config_file):
        self.config = {}
        if not config_file is None:
            self.config = self.load_properties(config_file)
    
    def load_properties(self, filepath, sep='=', comment_char='#', section_char='['):
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

    def getServerListeningHostName(self):
        serverHostName = DEFAULT_HOST_NAME
        if 'server.listening_hostname' in self.config:
            serverHostName = self.config['server.listening_hostname']
        
        return serverHostName
    
    def getServerListeningPort(self):
        serverPort = DEFAULT_PORT_NUMBER
        if 'server.listening_port' in self.config:
            serverPort = int(self.config['server.listening_port'])
        
        return serverPort
    
    def getKeyFile(self):
        keyFile = None
        if 'server.keyfile' in self.config:
            keyFile = self.config['server.keyfile']
        
        return keyFile

    def getCertFile(self):
        certFile = None
        if 'server.certfile' in self.config:
            certFile = self.config['server.certfile']
        
        return certFile
    
    def getServerServingHostName(self):
        serverHostName = self.getServerListeningHostName()
        if 'server.serving_hostname' in self.config and self.config['server.serving_hostname'] != '':
            serverHostName = self.config['server.serving_hostname']
        
        return serverHostName
