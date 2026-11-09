"""
GreenPulse – MongoDB async connection via Motor
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME     = os.getenv("DB_NAME", "greenpulse")

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    if os.getenv("TESTING") == "1":
        return

    try:
        real_client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=2000)
        await real_client.admin.command('ping')
        client = real_client
        db = client[DB_NAME]
        await create_indexes()
        print(f"✅  Connected to MongoDB: {DB_NAME}")
    except Exception as e:
        print(f"⚠️  Live MongoDB connection unavailable ({e}).")
        try:
            from mongomock_motor import AsyncMongoMockClient
            print("🚀  Initializing in-memory database engine for seamless local execution...")
            client = AsyncMongoMockClient()
            db = client[DB_NAME]
            print(f"✅  In-memory MongoDB active: {DB_NAME}")
        except Exception as mock_err:
            print(f"❌  Failed to initialize fallback database: {mock_err}")


async def close_db():
    global client
    if client:
        try:
            client.close()
            print("🔌  MongoDB connection closed")
        except Exception:
            pass


async def get_db():
    return db


async def create_indexes():
    """Create optimised indexes on all collections"""
    if db is None:
        return

    try:
        # Users
        await db.users.create_indexes([
            IndexModel([("email", ASCENDING)], unique=True),
            IndexModel([("role", ASCENDING)]),
        ])

        # Products
        await db.products.create_indexes([
            IndexModel([("name", TEXT), ("description", TEXT)]),
            IndexModel([("category", ASCENDING)]),
            IndexModel([("is_active", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ])

        # Services
        await db.services.create_indexes([
            IndexModel([("name", TEXT), ("description", TEXT)]),
            IndexModel([("category", ASCENDING)]),
            IndexModel([("is_active", ASCENDING)]),
        ])

        # Partners
        await db.partners.create_indexes([
            IndexModel([("company_name", TEXT)]),
            IndexModel([("is_active", ASCENDING)]),
        ])

        # Knowledge articles
        await db.knowledge_articles.create_indexes([
            IndexModel([("title", TEXT), ("content", TEXT), ("tags", TEXT)]),
            IndexModel([("category", ASCENDING)]),
            IndexModel([("is_published", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ])

        # Leads / inquiries
        await db.leads.create_indexes([
            IndexModel([("type", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("phone", ASCENDING)]),
        ])

        # Categories
        await db.categories.create_indexes([
            IndexModel([("slug", ASCENDING)], unique=True),
            IndexModel([("type", ASCENDING)]),
        ])

        # Testimonials
        await db.testimonials.create_indexes([
            IndexModel([("is_active", ASCENDING)]),
        ])

        print("📑  MongoDB indexes created")
    except Exception as e:
        print(f"Index creation notice: {e}")
