# test_redis.py
import os
import ssl
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

redis_url = os.environ.get("CELERY_BROKER_URL")
print(
    f"Testing connection to: {redis_url.split('@')[1] if '@' in redis_url else redis_url}"
)

try:
    # Handle SSL connections
    if redis_url.startswith("rediss://"):
        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Parse the URL and connect with SSL
        protocol, rest = redis_url.split("://", 1)
        auth, host_part = rest.split("@", 1)

        # Extract password
        if ":" in auth:
            user, password = auth.split(":", 1)
        else:
            user, password = "", auth

        # Extract host, port, db
        if "/" in host_part:
            host_port, db_part = host_part.split("/", 1)
            db = int(db_part.split("?")[0])
        else:
            host_port = host_part
            db = 0

        host, port = host_port.split(":")
        port = int(port)

        print(f"Connecting to: {host}:{port}/{db} with SSL")
        r = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            ssl=True,
            ssl_cert_reqs=ssl.CERT_NONE,
        )
    else:
        # Use from_url for non-SSL
        r = redis.from_url(redis_url)

    # Test connection
    print("Pinging Redis...")
    r.ping()
    print("Successfully connected to Redis!")

    # Test operations
    r.set("test_key", "test_value")
    value = r.get("test_key")
    print(f"Test value: {value}")

except Exception as e:
    print(f"Redis connection error: {str(e)}")
    import traceback

    traceback.print_exc()
