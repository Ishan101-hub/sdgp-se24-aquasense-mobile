# db.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")          # Atlas or local
MONGODB_DB = os.getenv("MONGODB_DB", "aquasense")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI missing in .env")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

# Export these (names must match your import)
readings_col = db["readings"]
events_col = db["events"]
