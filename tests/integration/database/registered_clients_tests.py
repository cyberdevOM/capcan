import pytest
import uuid
from datetime import datetime, timedelta
from src.server.core.database import Database

# ============== FIXTURES ==============
@pytest.fixture(scope="function")
def db():
    """Create a database connection for each test"""
    database = Database()
    yield database
    # Cleanup after test
    database.close()

@pytest.fixture(scope="function")
def test_client_id():
    """Generate a unique test client_id"""
    return str(uuid.uuid4())

@pytest.fixture(scope="function")
def test_client_data(test_client_id):
    """Standard test client data"""
    return {
        "client_id": test_client_id,
        "hostname": "test-client-01",
        "client_os": "linux",
        "client_secret": "test-secret-key-123",
        "description": "Test client for unit testing",
        "notes": "This client is used for testing the registered_clients table."
    }

@pytest.fixture(scope="function")
def registered_test_client(database, test_client_data):
    """Register a test client and clean up after the test"""
    database.register_client(**test_client_data)
    yield test_client_data["client_id"]
    # Cleanup: delete the test client
    database.delete_client(test_client_data["client_id"])


# ============== Client Registration Tests ==============
class TestClientRegistration:
    """ Test suite for client registration operations."""

    def test_register_client_success(self, database, test_client_data):
        """Test successful client registration."""
        res = database.register_client(**test_client_data)
        assert res is not None
        # Cleanup
        database.delete_client(test_client_data["client_id"])

    def test_register_client_duplicate(self, database, test_client_data, registered_test_client):
        """Test registering a client with a duplicate client_id."""
        with pytest.raises(Exception):
            database.register_client(**test_client_data)

    def test_register_client_missing_required_fields(self, database):
        """Test registration fails with required fields."""
        incomplete_data = {
            "client_id": str(uuid.uuid4()),
            # Missing hostname, client_os, and client_secret
        }
        with pytest.raises(Exception):
            database.register_client(**incomplete_data)

# ============== Client Retrieval Tests ==============
class TestClientRetrieval:
    """ Test suite for client retrieval operations."""
     
    def test_get_client_by_id_success(self, database, registered_test_client, test_client_data):
        """Test retrieving client by valid client_id."""
        res = database.get_client_by_id(registered_test_client)
        assert res is not None
        assert res[0] == test_client_data["client_id"] # first column is client_id

    def test_get_client_by_id_not_found(self, database):
        """Test retrieving non-existent client returns None."""
        res = database.get_client_by_id(str(uuid.uuid4())) # random client_id that doesn't exist
        assert res is None

    def test_get_all_clients(self, database, registered_test_client):
        """Test retrieving all clients."""
        res = database.get_all_clients()
        assert res is not None
        assert len(res) > 0 # should return at least the registered test client
    
    @pytest.mark.parameterize("search_param,search_value", [
        ("client_number", 1), 
        ("hostname", "test-client-01"),
        ("client_os", "linux")
    ])
    def test_get_client_id(self, database, registered_test_client, test_client_data, search_param, search_value):
        """Test retrieving client_id based on different search parameters."""
        if search_param == "hostname":
            res = database.get_client_id(hostname=search_value)
            assert res == test_client_data["client_id"]

# ============== Client Secret Tests ==============
class TestClientSecret:
    """ Test suite for client secret operations."""
    
    def test_get_client_secret_success(self, database, registered_test_client, test_client_data):
        """Test retrieving client secret."""
        secret = database.get_client_secret(registered_test_client)
        assert secret == test_client_data["client_secret"]

    def test_get_client_secret_not_found(self, database):
        """Test retrieving secret for non-existent client."""
        secret = database.get_client_secret(str(uuid.uuid4())) # random client_id that doesn't exist
        assert secret is None

# ============== Client Update Tests ==============
class TestClientUpdate:
    """ Test suite for client update operations."""

    def test_update_client_description(self, database, registered_test_client):
        """Test updating client description."""
        new_description = "Updated description"
        res = database.update_client(registered_test_client, description=new_description)
        assert res is True
        # Verify update
        client = database.get_client_by_id(registered_test_client)
        assert client[4] == new_description # description is the 5th column

    def test_update_client_secret(self, database, registered_test_client):
        """Test updating client secret."""
        new_secret = "new-secret-key-456"
        res = database.update_client(registered_test_client, secret=new_secret)
        assert res is True
        # Verify update
        secret = database.get_client_secret(registered_test_client)
        assert secret == new_secret

    def test_update_client_multiple_fields(self, database, registered_test_client):
        """Test updating multiple client fields simultaneously."""
        res = database.update_client(
            registered_test_client,
            description="Multi-field update",
            notes="Updated notes"
        )
        assert res is True

# ============== Client Revocation Tests ==============
class TestClientRevocation:
    """ Test suite for client revocation operations."""

    def test_revoke_client(self, database, registered_test_client):
        """Test revoking a client."""
        res = database.revoke_client(registered_test_client)
        assert res is True
        # Verify Revocation (check revoked flag)
        client = database.get_client_by_id(registered_test_client)
        assert client[-2] is True # revoked is the second to last column

# ============== Client Deletion Tests ==============
class TestClientDeletion:
    """ Test suite for client deletion operations."""

    def test_delete_client(self, database, test_client_data):
        """Test deleting a client."""
        database.register_client(**test_client_data)
        res = database.delete_client(test_client_data["client_id"])
        assert res is True
        # Verify Deletion
        client = database.get_client_by_id(test_client_data["client_id"])
        assert client is None

# ============= Integration Tests ==============
class TestClientIntegration:
    """ Integration tests for complete client workflows."""

    def test_full_client_lifecycle(self, database, test_client_data):
        """Test complete client lifecycle: register, retrieve, update, revoke, delete."""

        client_id = test_client_data["client_id"]

        # Register Client
        database.register_client(**test_client_data)
        res = database.get_client_by_id(client_id)
        assert res is not None

        # Update Client
        database.update_client(client_id, description="updated")
        res = database.get_client_by_id(client_id)
        assert res[4] == "updated"

        # Revoke Client
        database.revoke_client(client_id)
        # Verify Revocation
        res = database.get_client_by_id(client_id)
        assert res[-2] is True

        # Delete Client
        database.delete_client(client_id)
        res = database.get_client_by_id(client_id)
        assert res is None

    def test_multiple_client_filtering(self, database):
        """Test registering and filtering multiple clients."""
        clients = [
            {
                "client_id": str(uuid.uuid4()),
                "hostname": f"client-{i}",
                "client_os": "linux" if i % 2 == 0 else "windows",
                "client_secret": f"secret-{i}"
            }
            for i in range(3)
        ]

        # Register all
        for client in clients:
            database.register_client(**client)
        
        # Filter by xyz

        # cleanup
        for client in clients:
            db.delete_client(client["client_id"])