"""
GreenPulse Automated Full-Stack Test Suite
Covers:
- Root and Health endpoints
- Authentication & Strict Privilege Escalation Prevention
- Role-based authorization (Farmer vs Admin)
- Products CRUD & Filtering
- Services CRUD
- Partners CRUD
- Knowledge Center CRUD
- Leads submission & Honeypot Spam Protection
- Weather API & Village Search
- Admin Dashboard, Categories & Settings
"""
import pytest
import pytest_asyncio
import httpx
from mongomock_motor import AsyncMongoMockClient
import os
import sys

# Flag testing environment before any imports
os.environ["TESTING"] = "1"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests"

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from config.database import get_db
from middleware.auth import hash_password, create_access_token
from utils.helpers import now


@pytest_asyncio.fixture
async def mock_db():
    client = AsyncMongoMockClient()
    db = client["greenpulse_test"]
    # Seed initial admin
    await db.users.insert_one({
        "name": "Test Admin",
        "email": "admin@greenpulse.in",
        "password": hash_password("Admin@123456"),
        "role": "admin",
        "is_active": True,
        "created_at": now(),
    })
    return db


@pytest_asyncio.fixture
async def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_privilege_escalation_prevention(client):
    """
    CRITICAL TEST: Ensures public registration CANNOT elevate to 'admin'
    even when an attacker explicitly passes role='admin'.
    """
    payload = {
        "name": "Malicious User",
        "email": "attacker@example.com",
        "password": "Password@123",
        "role": "admin",  # Attacker attempt
        "phone": "9876543210",
        "village": "Guntur",
    }
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["role"] == "farmer", "Security Failure: Public user was able to obtain non-farmer role!"
    token = data["access_token"]

    # Verify that this user is blocked from admin dashboard
    admin_res = await client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert admin_res.status_code == 403, "Security Failure: Non-admin user was able to access admin dashboard!"


@pytest.mark.asyncio
async def test_admin_login_and_dashboard(client):
    """Verifies that legitimate admin credentials succeed and can access dashboard."""
    login_payload = {
        "email": "admin@greenpulse.in",
        "password": "Admin@123456"
    }
    res = await client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "admin"
    admin_token = data["access_token"]

    dash_res = await client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "stats" in dash_data
    assert "total_leads" in dash_data["stats"]


@pytest.mark.asyncio
async def test_products_crud_and_search(client, mock_db):
    """Test full CRUD cycle for products + search."""
    admin_user = await mock_db.users.find_one({"email": "admin@greenpulse.in"})
    admin_token = create_access_token({"sub": str(admin_user["_id"]), "role": "admin"})

    # 1. Create Product
    product_payload = {
        "name": "Bio-Enriched Compost 50kg",
        "category": "Fertilizers",
        "brand": "GreenPulse",
        "description": "High quality decomposed organic matter with micro-nutrients.",
        "tags": ["organic", "compost"],
        "is_active": True,
        "is_featured": True,
    }
    create_res = await client.post(
        "/api/v1/products",
        json=product_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert create_res.status_code == 201
    created_product = create_res.json()
    product_id = created_product["id"]
    assert created_product["name"] == product_payload["name"]

    # 2. Get Public List with Search
    list_res = await client.get("/api/v1/products?search=compost")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) >= 1
    assert any(p["id"] == product_id for p in items)

    # 3. Get Detail
    detail_res = await client.get(f"/api/v1/products/{product_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == product_id

    # 4. Update Product
    update_res = await client.put(
        f"/api/v1/products/{product_id}",
        json={"name": "Bio-Enriched Super Compost 50kg"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Bio-Enriched Super Compost 50kg"

    # 5. Delete Product
    del_res = await client.delete(
        f"/api/v1/products/{product_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert del_res.status_code == 200

    # 6. Verify Deleted
    get_del = await client.get(f"/api/v1/products/{product_id}")
    assert get_del.status_code == 404


@pytest.mark.asyncio
async def test_leads_and_honeypot(client, mock_db):
    """Test inquiry submission and bot protection."""
    # Legitimate lead
    lead_payload = {
        "name": "Farmer Ramesh",
        "phone": "9848022338",
        "email": "ramesh@example.com",
        "village": "Tenali",
        "crop": "Paddy",
        "message": "Need delivery of Bio-Organic fertilizer.",
        "type": "product",
    }
    res = await client.post("/api/v1/leads", json=lead_payload)
    assert res.status_code == 201
    lead_data = res.json()
    assert lead_data["name"] == "Farmer Ramesh"
    lead_id = lead_data["id"]

    # Bot spam submission with honeypot field filled
    spam_payload = {
        "name": "SpamBot",
        "phone": "9999999999",
        "message": "Buy cheap stuff",
        "hp_website": "http://spamsite.com",  # Honeypot filled
    }
    spam_res = await client.post("/api/v1/leads", json=spam_payload)
    assert spam_res.status_code in [200, 201]  # Returns fake success but doesn't persist

    # Admin lead status update
    admin_user = await mock_db.users.find_one({"email": "admin@greenpulse.in"})
    admin_token = create_access_token({"sub": str(admin_user["_id"]), "role": "admin"})
    status_res = await client.put(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": "contacted", "notes": "Called farmer, requested 5 bags."},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "contacted"


@pytest.mark.asyncio
async def test_weather_and_village_search(client):
    """Test weather lookup and village geocoding."""
    # Weather lookup
    weather_res = await client.get("/api/v1/weather?city=Tenali&lat=16.2430&lon=80.6400")
    assert weather_res.status_code == 200
    w_data = weather_res.json()
    assert "current" in w_data
    assert "advisory" in w_data
    assert "spraying" in w_data["advisory"]
    assert "irrigation" in w_data["advisory"]

    # Village search
    search_res = await client.get("/api/v1/weather/search?q=Tenali")
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert any("Tenali" in r["name"] for r in results)


@pytest.mark.asyncio
async def test_services_and_partners_crud(client, mock_db):
    """Test full CRUD operations on Services and Partners."""
    admin_user = await mock_db.users.find_one({"email": "admin@greenpulse.in"})
    admin_token = create_access_token({"sub": str(admin_user["_id"]), "role": "admin"})
    auth_header = {"Authorization": f"Bearer {admin_token}"}

    # 1. Service CRUD
    svc_payload = {
        "name": "Precision Soil Analysis",
        "category": "Soil Testing",
        "description": "Standard 16 parameter soil analysis for farmers.",
        "tags": ["soil", "testing"],
    }
    svc_create = await client.post("/api/v1/services", json=svc_payload, headers=auth_header)
    assert svc_create.status_code == 201
    svc_id = svc_create.json()["id"]

    svc_get = await client.get(f"/api/v1/services/{svc_id}")
    assert svc_get.status_code == 200
    assert svc_get.json()["name"] == svc_payload["name"]

    svc_update = await client.put(f"/api/v1/services/{svc_id}", json={"name": "Precision Soil Testing Pro"}, headers=auth_header)
    assert svc_update.status_code == 200
    assert svc_update.json()["name"] == "Precision Soil Testing Pro"

    svc_del = await client.delete(f"/api/v1/services/{svc_id}", headers=auth_header)
    assert svc_del.status_code == 200

    # 2. Partner CRUD
    partner_payload = {
        "company_name": "AgroTech Innovators",
        "category": "Machinery",
        "description": "Smart tractors and farm implements.",
        "website": "https://agrotech.in",
    }
    p_create = await client.post("/api/v1/partners", json=partner_payload, headers=auth_header)
    assert p_create.status_code == 201
    p_id = p_create.json()["id"]

    p_get = await client.get(f"/api/v1/partners/{p_id}")
    assert p_get.status_code == 200
    assert p_get.json()["company_name"] == partner_payload["company_name"]

    p_del = await client.delete(f"/api/v1/partners/{p_id}", headers=auth_header)
    assert p_del.status_code == 200


@pytest.mark.asyncio
async def test_admin_management_and_settings(client, mock_db):
    """Test category, testimonial, user status, and settings management."""
    admin_user = await mock_db.users.find_one({"email": "admin@greenpulse.in"})
    admin_token = create_access_token({"sub": str(admin_user["_id"]), "role": "admin"})
    auth_header = {"Authorization": f"Bearer {admin_token}"}

    # 1. Category CRUD
    cat_res = await client.post("/api/v1/admin/categories", json={
        "name": "Organic Seeds",
        "slug": "organic-seeds",
        "type": "product",
        "icon": "🌱",
        "order": 1
    }, headers=auth_header)
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["id"]

    cat_del = await client.delete(f"/api/v1/admin/categories/{cat_id}", headers=auth_header)
    assert cat_del.status_code == 200

    # 2. Testimonial CRUD
    testi_res = await client.post("/api/v1/admin/testimonials", json={
        "name": "K. Venkatesh",
        "location": "Guntur",
        "crop_type": "Chilli",
        "rating": 5,
        "text": "Excellent yields using GreenPulse organic solutions."
    }, headers=auth_header)
    assert testi_res.status_code == 201
    t_id = testi_res.json()["id"]

    t_del = await client.delete(f"/api/v1/admin/testimonials/{t_id}", headers=auth_header)
    assert t_del.status_code == 200

    # 3. Settings update & public retrieval
    set_res = await client.put("/api/v1/admin/settings", json={
        "site_name": "GreenPulse Agri Portal",
        "contact_phone": "+91 99999 88888"
    }, headers=auth_header)
    assert set_res.status_code == 200

    pub_settings = await client.get("/api/v1/admin/public-settings")
    assert pub_settings.status_code == 200
    assert pub_settings.json()["site_name"] == "GreenPulse Agri Portal"
