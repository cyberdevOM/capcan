class ClientServices():
    def __init__ (self, client):
        self.client = None
        self.client_id = None
        self.client_name = None
        self.client_ip = None
        self.client_port = None

    def add_client(self):
        pass
        # add logic to retrieve client information and call database method to add the client

    def remove_client(self):
        pass
        # add logic to retrieve client information and call database method to remove the client

    def edit_client(self):
        pass
        # add logic to retrieve client information and call database method to alter the client information

    def list_clients(self):
        pass
        # add logic to list all clients using the get_clients method from the database class and parse the results to desplay on the webserver.

class ClientDatabase():
    # This class Handles dataabase interactions for the clients table on the server side,
    # uses PostgreSQL as the database, and local temp config to store client information and reduce strain on the database.
    

    def __init__(self):
        self.clients = None

    def connect(self):
        pass
        # postgres connect to the database

    def disconnect(self):
        pass
        # postgres disconnect from the database

    def add_client(self, client):
        pass
        # postgres add new entity to the client table
    
    def remove_client(self, client_id):
        pass
        # postgres remove entity from the client table by client_id
    
    def alter_client(self, client):
        pass
        # postgres update entity in the client table by client_id
    
    def get_clients(self):
        pass
        # postgres get all entities from the client table
