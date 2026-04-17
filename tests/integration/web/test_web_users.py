import pytest
from src.server.core.database import Database
from src.server.utils.encryptors import hash_password, check_password, pre_hash_client_password
@pytest.fixture
def database():
    database = Database()
    yield database
    database.close()

@pytest.fixture(autouse=True)
def clean():
    db = Database()
    try:
        db.clear_table("auth")
        db.clear_table("user_permissions")
    except Exception as e:
        print(f"Cleanup failed: {e}")
        db.conn.rollback()

    yield  # wait for tests to run and then clean up after tests

    try:
        db.clear_table("auth")
        db.clear_table("user_permissions")
    except Exception as e:
        print(f"Cleanup failed: {e}")
        db.conn.rollback()
    finally:
        db.close()

def test_create_web_user(database):
    try:
        password = "test_password"
        client_hash = pre_hash_client_password(password)
        password_hash = hash_password(client_hash)

        database.create_web_user("test_user_name", password_hash, "test_email@example.com")

        assert check_password(client_hash, password_hash) == True

        database.cursor.execute("SELECT * FROM user_permissions WHERE display_name = 'test_user_name'")
        result = database.cursor.fetchone()
        assert result is not None
    except Exception as e:
        pytest.fail(f"Failed to create web user: {e}")

def test_get_web_user(database):
    try:
        test_create_web_user(database)  # Ensure a user is created for retrieval

        user_id = database.get_web_user_id("test_user_name")
        assert user_id is not None
        user = database.get_web_user("test_user_name")
        assert user is not None
        # display_name is at index 2 in user_permissions table
        assert user[2] == "test_user_name"
    except Exception as e:
        pytest.fail(f"Failed to get web user: {e}")

def test_get_user_auth(database):
    try:
        test_create_web_user(database)  # Ensure a user is created for retrieval

        auth = database.get_user_auth("test_user_name")
        assert auth is not None
        # get_user_auth returns the password hash string directly
        assert check_password(pre_hash_client_password("test_password"), auth) == True
    except Exception as e:
        pytest.fail(f"Failed to get user auth: {e}")
