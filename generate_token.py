import jwt
import time

# A secret key for signing the token.
# In a real application, this should be kept secret and not hard-coded.
SECRET_KEY = "your-secret-key"

# The issuer and audience should match the values in the MCP server configuration.
ISSUER = "https://example.com/"
AUDIENCE = "my-mcp-server"

def create_jwt():
    """
    Creates a new JWT.
    """
    payload = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": int(time.time()) + 3600,  # Token expires in 1 hour
        "iat": int(time.time()),
        "sub": "user123",  # Example subject
    }
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

if __name__ == "__main__":
    token = create_jwt()
    print("Generated JWT:")
    print(token)
