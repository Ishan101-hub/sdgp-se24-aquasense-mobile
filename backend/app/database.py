from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URL, DB_NAME

# Motor is the async version of PyMongo — we use it because FastAPI is async
# tls=True is required for MongoDB Atlas connections
# tlsAllowInvalidCertificates=True fixes SSL handshake errors on some networks
client = AsyncIOMotorClient(
    MONGO_URL,
    tls=True,
    tlsAllowInvalidCertificates=True
)

# Connect to the specific database inside our MongoDB Atlas cluster
database = client[DB_NAME]

# COLLECTIONS - Think of these like tables in a regular SQL database

# Stores all registered users — email, password, OTP, profile info etc.
users_collection = database.get_collection("users")

# Stores tokens that have been invalidated by logout
# Every request checks this before allowing access
blacklisted_tokens_collection = database.get_collection("blacklisted_tokens")

# Stores water related data — readings, sensor data etc.
water_data_collection = database.get_collection("water_data")

# Tracks failed login attempts per email address
# Used to lock accounts after too many wrong password attempts
failed_attempts_collection = database.get_collection("failed_attempts")