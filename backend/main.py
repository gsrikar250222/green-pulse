"""
GreenPulse – Production-Ready Agriculture Platform Backend
FastAPI + MongoDB Atlas + JWT Auth + Cloudinary + Open-Meteo
"""
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import sys

# Ensure backend directory is in sys.path when imported from root (e.g. Vercel backend.main:app)
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import time
from collections import defaultdict

from config.database import connect_db, close_db, get_db
from middleware.auth import hash_password
from utils.helpers import now

from routes.auth      import router as auth_router
from routes.products  import router as products_router
from routes.services  import router as services_router
from routes.partners  import router as partners_router
from routes.knowledge import router as knowledge_router
from routes.leads     import router as leads_router
from routes.weather   import router as weather_router
from routes.admin     import router as admin_router

load_dotenv()

# ── App Lifespan ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("TESTING") != "1":
        await connect_db()
        await seed_initial_data()
    yield
    if os.getenv("TESTING") != "1":
        await close_db()


# ── App Instance ─────────────────────────────────────

app = FastAPI(
    title       = "GreenPulse API",
    description = "India's premier agriculture platform connecting farmers with products, services, expert knowledge, and live weather advisories",
    version     = "2.0.0",
    lifespan    = lifespan,
    docs_url    = "/api/docs",
    redoc_url   = "/api/redoc",
)

# ── Security & Rate Limiting Middleware ──────────────

RATE_LIMIT_BUCKETS = defaultdict(list)
RATE_LIMIT_CONFIG = {
    "/api/v1/auth/login":    (15, 60),   # 15 attempts per 60 seconds
    "/api/v1/auth/register": (10, 60),   # 10 attempts per 60 seconds
    "/api/v1/leads":         (25, 60),   # 25 inquiries per 60 seconds
}

@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    # 1. Rate Limiting for sensitive endpoints
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path

    if request.method == "POST" and path in RATE_LIMIT_CONFIG:
        limit, window = RATE_LIMIT_CONFIG[path]
        current_time = time.time()
        bucket_key = f"{client_ip}:{path}"
        
        # Clean older requests outside window
        RATE_LIMIT_BUCKETS[bucket_key] = [
            t for t in RATE_LIMIT_BUCKETS[bucket_key] if current_time - t < window
        ]

        if len(RATE_LIMIT_BUCKETS[bucket_key]) >= limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please wait a minute and try again."},
                headers={"Retry-After": str(window)}
            )
        RATE_LIMIT_BUCKETS[bucket_key].append(current_time)

    # 2. Process Request
    response: Response = await call_next(request)

    # 3. Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(self), microphone=()"

    return response


# ── Dynamic CORS Configuration ───────────────────────

raw_frontend_urls = os.getenv("FRONTEND_URL", "http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500")
allowed_origins = [url.strip() for url in raw_frontend_urls.split(",") if url.strip()]
for fallback in ["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:3000", "http://localhost:8000"]:
    if fallback not in allowed_origins:
        allowed_origins.append(fallback)

app.add_middleware(
    CORSMiddleware,
    allow_origins         = allowed_origins,
    allow_origin_regex    = r"https://.*\.vercel\.app",  # Automatically permit all Vercel preview & production domains
    allow_credentials     = True,
    allow_methods         = ["*"],
    allow_headers         = ["*"],
)


# ── Routers (Standardized under /api/v1) ──────────────

API = "/api/v1"

app.include_router(auth_router,      prefix=API)
app.include_router(products_router,  prefix=API)
app.include_router(services_router,  prefix=API)
app.include_router(partners_router,  prefix=API)
app.include_router(knowledge_router, prefix=f"{API}/knowledge")
app.include_router(knowledge_router, prefix=f"{API}/articles")
app.include_router(leads_router,     prefix=API)
app.include_router(weather_router,   prefix=API)
app.include_router(admin_router,     prefix=API)


# ── Health, Favicon & Diagnostics ────────────────────

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(
        content='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🌱</text></svg>'.encode("utf-8"),
        media_type="image/svg+xml"
    )

@app.get("/api/debug-files", include_in_schema=False)
async def debug_files():
    cur = os.path.abspath(".")
    files_cur = os.listdir(".") if os.path.exists(".") else []
    parent = os.path.abspath("..")
    files_parent = os.listdir("..") if os.path.exists("..") else []
    file_dir = os.path.dirname(os.path.abspath(__file__))
    files_file_dir = os.listdir(file_dir) if os.path.exists(file_dir) else []
    return {
        "cwd": cur,
        "files_cur": files_cur,
        "parent": parent,
        "files_parent": files_parent,
        "file_dir": file_dir,
        "files_file_dir": files_file_dir,
    }

@app.get("/api", tags=["Health"])
@app.get("/api/info", tags=["Health"])
async def api_info():
    return {
        "status": "ok",
        "app": "GreenPulse API",
        "version": "2.0.0",
        "timestamp": now().isoformat(),
        "docs": "/api/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "service": "greenpulse-backend"}


# ── Database Seeding Logic ───────────────────────────

async def seed_initial_data():
    """Initializes admin user, categories, and essential demo data on fresh deployment."""
    db = await get_db()
    if db is None:
        return

    admin_email    = os.getenv("ADMIN_EMAIL", "admin@greenpulse.in").lower().strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@123456")

    # 1. Seed Admin
    existing_admin = await db.users.find_one({"email": admin_email})
    if not existing_admin:
        await db.users.insert_one({
            "name":       "GreenPulse Chief Administrator",
            "email":      admin_email,
            "password":   hash_password(admin_password),
            "role":       "admin",
            "is_active":  True,
            "created_at": now(),
            "updated_at": None,
        })
        print(f"🌱  Admin user seeded: {admin_email}")

    # 2. Seed Default Categories
    default_categories = [
        {"name": "Fertilizers",      "slug": "fertilizers",      "type": "product", "icon": "🌱", "order": 1},
        {"name": "Pesticides",       "slug": "pesticides",       "type": "product", "icon": "🐛", "order": 2},
        {"name": "Seeds",            "slug": "seeds",            "type": "product", "icon": "🌾", "order": 3},
        {"name": "Equipment",        "slug": "equipment",        "type": "product", "icon": "🚜", "order": 4},
        {"name": "Organic Products", "slug": "organic-products", "type": "product", "icon": "🍃", "order": 5},
        {"name": "Consultation",     "slug": "consultation",     "type": "service", "icon": "👨‍🌾", "order": 1},
        {"name": "Soil Testing",     "slug": "soil-testing",     "type": "service", "icon": "🧪", "order": 2},
        {"name": "Irrigation",       "slug": "irrigation",       "type": "service", "icon": "💧", "order": 3},
        {"name": "Equipment Rental", "slug": "equipment-rental", "type": "service", "icon": "🔧", "order": 4},
        {"name": "Crop Guides",      "slug": "crop-guides",      "type": "article", "icon": "📖", "order": 1},
        {"name": "Fertilizer Info",  "slug": "fertilizer-info",  "type": "article", "icon": "🌱", "order": 2},
        {"name": "Weather Tips",     "slug": "weather-tips",     "type": "article", "icon": "🌤", "order": 3},
        {"name": "Irrigation Tips",  "slug": "irrigation-tips",  "type": "article", "icon": "💧", "order": 4},
        {"name": "Partner Articles", "slug": "partner-articles", "type": "article", "icon": "🤝", "order": 5},
    ]

    for cat in default_categories:
        if not await db.categories.find_one({"slug": cat["slug"]}):
            await db.categories.insert_one({**cat, "created_at": now()})

    # 3. Seed Default Site Settings
    if not await db.site_settings.find_one({}):
        await db.site_settings.insert_one({
            "site_name":        os.getenv("APP_NAME", "GreenPulse"),
            "tagline":          "Growing India's Agriculture",
            "contact_phone":    "+91 98765 43210",
            "contact_email":    "hello@greenpulse.in",
            "contact_address":  "Guntur, Andhra Pradesh, India",
            "whatsapp_number":  os.getenv("WHATSAPP_NUMBER", "919876543210"),
            "facebook_url":     "https://facebook.com/greenpulse",
            "instagram_url":    "https://instagram.com/greenpulse",
            "twitter_url":      "https://twitter.com/greenpulse",
            "meta_title":       "GreenPulse – India's Premier Agriculture Platform",
            "meta_description": "GreenPulse connects farmers with certified products, soil testing, drone spraying services, expert advisories and live weather.",
            "created_at":       now(),
            "updated_at":       now(),
        })

    # 4. Seed Seed Products if catalog is empty
    product_count = await db.products.count_documents({})
    if product_count == 0:
        seed_products = [
            {
                "name": "Bio-Organic Growth Formula Pro",
                "category": "Fertilizers",
                "sub_category": "Organic",
                "brand": "GreenPulse AgriTech",
                "description": "Premium 100% organic microbial fertilizer enriched with humic acid, mycorrhiza, and bio-active micro-nutrients. Enhances root proliferation, improves soil CEC, and increases yield by 20-30% across Paddy, Cotton, and Chilli.",
                "tags": ["organic", "fertilizer", "growth", "paddy", "soil-health"],
                "images": ["https://images.unsplash.com/photo-1585314062340-f1a5a7c9328d?w=800&q=80&fit=crop"],
                "is_active": True,
                "is_featured": True,
                "whatsapp_msg": "I am interested in ordering Bio-Organic Growth Formula Pro. Please share pricing and bulk delivery details.",
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "name": "NeemShield Botanical Insecticide",
                "category": "Pesticides",
                "sub_category": "Botanical",
                "brand": "EcoAgro India",
                "description": "Cold-pressed pure azadirachtin 10,000 PPM botanical pesticide. Provides broad-spectrum control against whiteflies, aphids, thrips, and bollworms without killing beneficial pollinators.",
                "tags": ["neem", "pesticides", "eco-friendly", "cotton", "chilli"],
                "images": ["https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=800&q=80"],
                "is_active": True,
                "is_featured": True,
                "whatsapp_msg": "I want to inquire about NeemShield Botanical Insecticide.",
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "name": "Kaveri Super Hybrid Paddy BPT-5204",
                "category": "Seeds",
                "sub_category": "Hybrid",
                "brand": "Kaveri Seeds",
                "description": "High-yielding, blast-resistant fine grain hybrid paddy seeds with 140-day maturity. Excellent milling quality, slender grain, and superior grain cooking characteristics.",
                "tags": ["seeds", "paddy", "hybrid", "high-yield"],
                "images": ["https://images.unsplash.com/photo-1536304929831-ee1ca9d44906?w=800&q=80&fit=crop"],
                "is_active": True,
                "is_featured": True,
                "whatsapp_msg": "Please share availability and dealer location for Kaveri Super Hybrid Paddy Seeds.",
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "name": "Solan Precision Micro-Drip Irrigation Kit",
                "category": "Equipment",
                "sub_category": "Irrigation",
                "brand": "Netafim Partner",
                "description": "Complete 1-acre precision drip irrigation kit with pressure-compensating drippers, disc filter, venturi fertilizer injector, and UV-stabilized lateral tubing. Saves up to 60% water.",
                "tags": ["irrigation", "drip", "equipment", "water-saving"],
                "images": ["https://images.unsplash.com/photo-1563514227147-6d2ff665a6a0?w=800&q=80&fit=crop"],
                "is_active": True,
                "is_featured": True,
                "whatsapp_msg": "Need quote and subsidy guidance for Solan Precision Micro-Drip Irrigation Kit.",
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "name": "Trichoderma Viride Bio-Fungicide",
                "category": "Organic Products",
                "sub_category": "Bio-Control",
                "brand": "GreenPulse Bio",
                "description": "Antagonistic fungal biocontrol agent for seed treatment and soil application. Highly effective against damping-off, collar rot, wilt, and root rot in groundnut, pulses, and vegetables.",
                "tags": ["bio-fungicide", "organic", "seed-treatment"],
                "images": ["https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?w=800&q=80&fit=crop"],
                "is_active": True,
                "is_featured": False,
                "whatsapp_msg": "Inquiry regarding Trichoderma Viride Bio-Fungicide application dosage.",
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "name": "Smart Heavy-Duty Knapsack Battery Sprayer 16L",
                "category": "Equipment",
                "sub_category": "Sprayers",
                "brand": "AgroMax Tools",
                "description": "Rechargeable 12V 12Ah lithium-ion battery sprayer with continuous 6-hour runtime, dual speed pressure regulator, telescopic stainless steel lance, and 4 specialized nozzles.",
                "tags": ["equipment", "sprayer", "battery", "tools"],
                "images": ["https://images.unsplash.com/photo-1615811361523-6bd03d7748e7?w=800&q=80&fit=crop"],
                "is_active": True,
                "is_featured": False,
                "whatsapp_msg": "I want to purchase the Smart Heavy-Duty Battery Sprayer 16L.",
                "created_at": now(),
                "updated_at": now(),
            },
        ]
        await db.products.insert_many(seed_products)
        print("🌾  Default product catalog seeded")

    # 5. Seed Services if empty
    service_count = await db.services.count_documents({})
    if service_count == 0:
        seed_services = [
            {
                "name": "Scientific Soil Health & Micronutrient Testing",
                "category": "Soil Testing",
                "description": "Comprehensive laboratory analysis measuring pH, Electrical Conductivity (EC), Organic Carbon (OC), available Nitrogen, Phosphorus, Potassium, Zinc, and Boron. Includes village doorstep sample collection and digital Soil Health Card.",
                "details": "Turnaround time: 48 hours. Report issued in Telugu and English with tailored fertilizer prescription.",
                "tags": ["soil-test", "npk", "doorstep", "laboratory"],
                "images": ["https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=800&q=80"],
                "is_active": True,
                "is_featured": True,
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "name": "Automated Drone Aerial Spraying Service",
                "category": "Equipment Rental",
                "description": "DGCA-certified drone pilots providing ultra-precise foliar nutrient and pesticide application. Covers 1 acre in 7-10 minutes with 90% water savings and zero chemical exposure to farm laborers.",
                "details": "Operates across Guntur, Krishna, Prakasam, and Godavari districts. Advance booking available.",
                "tags": ["drone", "spraying", "precision-agri", "water-saving"],
                "images": ["https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=800&q=80&fit=crop"],
                "is_active": True,
                "is_featured": True,
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "name": "One-on-One Agronomist Field Consultation",
                "category": "Consultation",
                "description": "Certified agricultural scientists visit your farm for pest diagnosis, disease management, irrigation scheduling, and harvest planning tailored to your exact soil type and crop variety.",
                "details": "Weekly or monthly advisory visits with instant WhatsApp support for crop queries.",
                "tags": ["agronomist", "expert-visit", "crop-doctor", "consulting"],
                "images": ["https://images.unsplash.com/photo-1595974482597-4b8da8879bc5?w=800&q=80&fit=crop"],
                "is_active": True,
                "is_featured": True,
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "name": "Smart Drip Irrigation Design & Installation",
                "category": "Irrigation",
                "description": "End-to-end drip and sprinkler irrigation planning, pipeline layout engineering, government subsidy documentation assistance, and professional field installation with 3-year maintenance warranty.",
                "details": "Specialized layouts for orchard crops (Mango, Sweet Lime), Chilli, Cotton, and vegetable farming.",
                "tags": ["drip", "irrigation", "installation", "subsidy"],
                "images": ["https://images.unsplash.com/photo-1563514227147-6d2ff665a6a0?w=800&q=80&fit=crop"],
                "is_active": True,
                "is_featured": False,
                "created_at": now(),
                "updated_at": now(),
            },
        ]
        await db.services.insert_many(seed_services)
        print("⚙️  Default services seeded")

    # 6. Seed Partner Brands if empty
    partner_count = await db.partners.count_documents({})
    if partner_count == 0:
        seed_partners = [
            {
                "company_name": "IFFCO (Indian Farmers Fertiliser Cooperative)",
                "category": "Fertilizers & Nano Bio-Tech",
                "description": "India's leading cooperative manufacturing world-class Nano Urea, Nano DAP, and bio-fertilizers empowering millions of smallholders.",
                "website": "https://iffco.in",
                "email": "contact@iffco.in",
                "phone": "1800-103-1967",
                "address": "IFFCO Sadan, C-1, District Centre, Saket, New Delhi",
                "logo_url": "https://images.unsplash.com/photo-1595974482597-4b8da8879bc5?w=200&q=80&fit=crop",
                "images": [],
                "is_active": True,
                "is_featured": True,
                "created_at": now(),
            },
            {
                "company_name": "Bayer CropScience India",
                "category": "Crop Protection & Hybrid Seeds",
                "description": "Global innovator offering high-performing crop protection solutions, biological inputs, and hybrid seeds for sustainable agriculture.",
                "website": "https://bayer.in",
                "email": "cropscience@bayer.com",
                "phone": "+91 22 2531 1234",
                "address": "Bayer House, Central Avenue, Hiranandani Estate, Thane",
                "logo_url": "https://images.unsplash.com/photo-1536304929831-ee1ca9d44906?w=200&q=80&fit=crop",
                "images": [],
                "is_active": True,
                "is_featured": True,
                "created_at": now(),
            },
            {
                "company_name": "Mahindra & Mahindra Farm Equipment",
                "category": "Farm Machinery & Tractors",
                "description": "World's largest tractor manufacturer by volume, empowering farmers with smart mechanization, implements, and rental tools.",
                "website": "https://mahindratractor.com",
                "email": "farmequipment@mahindra.com",
                "phone": "1800-425-6576",
                "address": "Mahindra Towers, Worli, Mumbai",
                "logo_url": "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=200&q=80&fit=crop",
                "images": [],
                "is_active": True,
                "is_featured": True,
                "created_at": now(),
            },
            {
                "company_name": "Netafim Agricultural Financing & Irrigation",
                "category": "Precision Drip & Micro-Irrigation",
                "description": "Pioneers of drip irrigation delivering smart automated fertigation, subsurface drip systems, and water conservation technologies.",
                "website": "https://netafimindia.com",
                "email": "info@netafimindia.com",
                "phone": "1800-103-2600",
                "address": "Netafim House, Vadodara, Gujarat",
                "logo_url": "https://images.unsplash.com/photo-1563514227147-6d2ff665a6a0?w=200&q=80&fit=crop",
                "images": [],
                "is_active": True,
                "is_featured": True,
                "created_at": now(),
            },
        ]
        await db.partners.insert_many(seed_partners)
        print("🤝  Default partner brands seeded")

    # 7. Seed Knowledge Articles if empty
    article_count = await db.knowledge_articles.count_documents({})
    if article_count == 0:
        seed_articles = [
            {
                "title": "Comprehensive Kharif Paddy Management: Sowing to Post-Harvest",
                "category": "Crop Guides",
                "author_name": "Dr. K. Ramana Murthy, Senior Agronomist",
                "excerpt": "Essential guide for Andhra & Telangana paddy growers covering nursery preparation, water management, AWD technique, and brown planthopper control.",
                "content": """
### 1. Nursery Management and Seed Treatment
Treat seeds with Carbendazim 2g/kg or Trichoderma viride 10g/kg 24 hours before soaking. Use wet nursery bed technique with 100m² nursery area per acre.

### 2. Main Field Preparation & Alternate Wetting and Drying (AWD)
Incorporate 5 tonnes of well-rotted FYM or green manure (Dhaincha) during puddling. Install an AWD perforated field pipe to monitor standing water depth; irrigate only when water level drops 15cm below the soil surface to conserve 25-30% irrigation water without yield penalty.

### 3. Integrated Nutrient Schedule
- **Basal**: Apply full dose of Phosphorus (DAP 50kg) + 25% Nitrogen (Urea 25kg) + 50% Potash (MOP 20kg).
- **Tillering (20-25 DAT)**: Top dress 35% Nitrogen + Zinc Sulphate 10kg/acre.
- **Panicle Initiation (45-50 DAT)**: Apply remaining 40% Nitrogen + 50% Potash.

### 4. Major Pest Surveillance
Monitor for Yellow Stem Borer and Brown Planthopper (BPH). Avoid excessive chemical nitrogen; maintain alleyways (badi batteelu) every 2 meters for aeration. Spray Chlorantraniliprole 18.5% SC @ 60ml/acre for stem borer.
                """.strip(),
                "tags": ["paddy", "kharif", "irrigation", "fertilizer", "pest-management"],
                "featured_image": "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?w=1200&q=80&fit=crop",
                "is_published": True,
                "is_featured": True,
                "views": 248,
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "title": "Chilli Black Thrips & Leaf Curl: Integrated Bio-Chemical Control",
                "category": "Fertilizer Info",
                "author_name": "P. Lakshmi Narayana, Plant Pathologist",
                "excerpt": "Scientific management protocol for invasive black thrips (Thrips parvispinus) and leaf curl virus in Andhra Pradesh chilli belt.",
                "content": """
### Understanding Thrips parvispinus
The invasive black thrips attacks chilli flowers and leaves, causing flower drop and characteristic upwards leaf curl.

### Step-by-Step IPM Protocol
1. **Blue & Yellow Sticky Traps**: Install 30 blue sticky traps and 20 yellow sticky traps per acre at crop canopy height.
2. **Neem Barrier**: Spray Azadirachtin 10,000 PPM @ 2ml/litre water every 10 days as a natural repellent.
3. **Bio-agent Inoculation**: Spray Lecanicillium lecanii @ 5g/litre during cloudy weather or evening hours.
4. **Targeted Chemistry**: When pest count exceeds 5 thrips per flower, rotate Spinetoram 11.7% SC @ 180ml/acre or Broflanilide 300 SC @ 20ml/acre. Never spray the same chemical consecutively.
                """.strip(),
                "tags": ["chilli", "thrips", "pest-control", "guntur", "integrated-pest-management"],
                "featured_image": "https://images.unsplash.com/photo-1588252303782-cb80119abd6d?auto=format&fit=crop&w=1200&q=80",
                "is_published": True,
                "is_featured": True,
                "views": 412,
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "title": "Soil Organic Carbon: How to Revitalize Exhausted Farm Soils",
                "category": "Crop Guides",
                "author_name": "GreenPulse Soil Science Cell",
                "excerpt": "Simple actionable techniques to lift soil organic carbon from 0.3% to over 0.8% for improved water retention and fertilizer use efficiency.",
                "content": """
Healthy soil must contain at least 0.75% Organic Carbon. Most agricultural soils across South India have degraded to under 0.4%, leading to soil compaction and high fertilizer wastage.

### Strategies to Rebuild Soil Organic Carbon:
1. **Green Manuring**: Sow Sunnhemp (Janumu) or Sesbania (Dhaincha) with pre-monsoon showers and plough into the soil at 45 days (50% flowering).
2. **Crop Residue Incorporation**: Cease burning paddy stubble and cotton stalks; shred residues and apply Trichoderma viride + cow dung slurry to accelerate decomposition.
3. **Vermicompost & Farm Yard Manure**: Apply 2-3 tonnes per acre during summer ploughing.
4. **Mulching**: Use crop straw or biological ground cover to prevent solar degradation of soil microbial biomass.
                """.strip(),
                "tags": ["soil-health", "organic-carbon", "compost", "green-manure"],
                "featured_image": "https://images.unsplash.com/photo-1605000797499-95a51c5269ae?auto=format&fit=crop&w=1200&q=80",
                "is_published": True,
                "is_featured": False,
                "views": 189,
                "created_at": now(),
                "updated_at": now(),
            },
        ]
        await db.knowledge_articles.insert_many(seed_articles)
        print("📚  Default knowledge articles seeded")

    # 8. Seed Testimonials if empty
    testimonial_count = await db.testimonials.count_documents({})
    if testimonial_count == 0:
        seed_testimonials = [
            {
                "name": "B. Srinivasa Rao",
                "location": "Tenali Mandal, Guntur",
                "crop_type": "Paddy (BPT-5204)",
                "rating": 5,
                "text": "Using GreenPulse soil testing and bio-fertilizer guidance, my fertilizer cost reduced by 25% and my paddy yield increased to 38 bags per acre. The Telugu advisories on WhatsApp helped me save my crop during unseasonal rain.",
                "photo_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&q=80&fit=crop",
                "is_active": True,
                "created_at": now(),
            },
            {
                "name": "K. Venkata Subbamma",
                "location": "Chilakaluripet, Palnadu",
                "crop_type": "Chilli (Teja Variety)",
                "rating": 5,
                "text": "The drone spraying service booked through GreenPulse covered my 4-acre chilli farm in just 35 minutes. Zero laborer hassle, even chemical spread, and excellent control over black thrips. Highly recommend to all farmers!",
                "photo_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&q=80&fit=crop",
                "is_active": True,
                "created_at": now(),
            },
            {
                "name": "M. Anjaneyulu",
                "location": "Gudivada, Krishna District",
                "crop_type": "Paddy & Blackgram",
                "rating": 5,
                "text": "Genuine products with doorstep delivery. The agronomist consultation was eye-opening for micronutrient management. It feels great to have a modern agriculture platform dedicated to Telugu farmers.",
                "photo_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&q=80&fit=crop",
                "is_active": True,
                "created_at": now(),
            },
        ]
        await db.testimonials.insert_many(seed_testimonials)
        print("💬  Default farmer testimonials seeded")


# ── Frontend & Root Route Handling ─────────────────────────────────────────

def _resolve_frontend_dir():
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"),
        os.path.join(os.getcwd(), "frontend"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(os.path.join(c, "index.html")):
            return c
    return None

frontend_dir = _resolve_frontend_dir()

if frontend_dir:
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    @app.get("/", include_in_schema=False)
    async def serve_index(request: Request):
        if "application/json" in request.headers.get("accept", "") and "text/html" not in request.headers.get("accept", ""):
            return {
                "status": "ok",
                "app": "GreenPulse API",
                "version": "2.0.0",
                "timestamp": now().isoformat(),
                "docs": "/api/docs",
            }
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/admin", include_in_schema=False)
    async def serve_admin():
        return FileResponse(os.path.join(frontend_dir, "admin.html"))

    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    async def root_api():
        return {
            "status": "online",
            "app": "GreenPulse Agriculture API",
            "version": "2.0.0",
            "message": "Welcome to GreenPulse API. The interactive Swagger documentation is available at /api/docs",
            "docs": "/api/docs",
            "endpoints": {
                "products": "/api/v1/products",
                "services": "/api/v1/services",
                "partners": "/api/v1/partners",
                "knowledge": "/api/v1/knowledge",
                "weather": "/api/v1/weather",
                "health": "/health"
            }
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
