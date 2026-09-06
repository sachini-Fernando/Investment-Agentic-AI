"""
Test script to verify .env loading.
"""

from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

print("=" * 50)
print("ENVIRONMENT VARIABLES CHECK")
print("=" * 50)

# Check each variable
keys = [
    "GOOGLE_API_KEY",
    "MONGODB_URI",
    "MONGODB_DB_NAME",
    "NEWS_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
]

for key in keys:
    value = os.getenv(key)
    if value:
        # Mask sensitive data
        masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
        print(f"✅ {key}: {masked}")
    else:
        print(f"❌ {key}: NOT FOUND")

# Test MongoDB connection
if os.getenv("MONGODB_URI"):
    try:
        from pymongo import MongoClient
        client = MongoClient(os.getenv("MONGODB_URI"), serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("\n✅ MongoDB connection successful!")
    except Exception as e:
        print(f"\n❌ MongoDB connection failed: {e}")
else:
    print("\n❌ MONGODB_URI not found in environment")