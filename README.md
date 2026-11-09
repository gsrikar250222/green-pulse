# 🌿 GreenPulse – Agriculture Platform (Production Ready)

> India's premier full-stack agriculture platform connecting farmers with products, services, expert knowledge, real-time agricultural weather intelligence, and partner brands.

---

## 📁 Project Structure

```
greenpulse/
├── frontend/
│   ├── index.html          # Main website (Homepage, dynamic grids, Telugu/English, Farmer portal)
│   └── admin.html          # Admin dashboard (CRUD, leads management, CSV export, Cloudinary upload)
├── backend/
│   ├── main.py             # FastAPI application, rate limiting, security headers, CORS, seeds
│   ├── requirements.txt    # Production dependencies (FastAPI, Motor, Bcrypt, Cloudinary, etc.)
│   ├── Procfile            # Render / Railway process definition
│   ├── render.yaml         # Render Infrastructure-as-Code blueprint
│   ├── .env.example        # Comprehensive environment variables reference
│   ├── config/
│   │   ├── database.py     # MongoDB Atlas connection (Motor async) + indexes
│   │   └── cloudinary.py   # Cloudinary integration + high-speed local data-URI fallback
│   ├── middleware/
│   │   └── auth.py         # JWT auth, direct bcrypt hashing, require_admin, optional_user
│   ├── models/
│   │   └── schemas.py      # Pydantic schemas (User, Product, Service, Partner, Lead, Article)
│   ├── routes/
│   │   ├── auth.py         # /auth — register (secure farmer), login, logout, me, password change
│   │   ├── products.py     # /products — search, category filter, CRUD, multiple image upload
│   │   ├── services.py     # /services — search, CRUD, image upload
│   │   ├── partners.py     # /partners — search, category filter, logo/gallery upload
│   │   ├── knowledge.py    # /articles — search, view count, publish toggle, CRUD
│   │   ├── leads.py        # /leads — inquiry intake, honeypot bot trap, status update, CSV export
│   │   ├── weather.py      # /weather — Open-Meteo live proxy, 30+ AP/TS mandals, smart advisories
│   │   └── admin.py        # /admin — dashboard stats, categories, testimonials, users, settings
│   ├── utils/
│   │   └── helpers.py      # MongoDB ObjectId serialization, pagination, slugify
│   └── tests/
│       ├── test_api.py     # 8 integration test suites (100% passing)
│       └── verify_frontend.py # Automated structural validator for HTML & JS
├── vercel.json             # Vercel deployment with cleanUrls, security headers & routing
├── .gitignore
└── README.md
```

---

## 🎨 Premium Editorial Visual Design System

GreenPulse has been upgraded with a bespoke editorial aesthetic inspired by leading global publication design and modern AgriTech:

- **Natural Forest Green & Ivory Palette**: Warm, artisanal organic ivory surfaces (`#FAF8F4` and `#F4EFE6`) balanced with deep cinematic forest emeralds (`#0B2212` and `#061509`) and subtle harvest gold accents (`#D4A373`).
- **Authentic Indian Agriculture Photography**: Replaced repetitive and generic stock photos with curated, high-resolution authentic imagery depicting Indian farmers, Andhra Pradesh and Telangana rice terraces, high-tech polyhouse greenhouses, micro-irrigation systems, and autonomous spraying drones.
- **GSAP & ScrollTrigger Animation**: Subtle Ken-Burns zoom and parallax on hero slides, staggered card entrance reveals, and responsive performance with `@media (prefers-reduced-motion: reduce)` accessibility compliance.
- **Swiper 11 Touch Carousels**: Inertia-based touch-swipe physics and pagination dots for service and product explorations on mobile, tablet, and desktop.
- **PhotoSwipe 5 Fullscreen Lightbox**: 60fps fullscreen viewing with pinch-to-zoom, keyboard navigation, and captions on all gallery and agricultural artwork assets.
- **Vanilla LazyLoad & Automatic WebP/AVIF**: Zero layout shifts (`aspect-ratio: 16/11`, `4/3`, `1/1`), responsive srcset, and `auto=format` image compression.

---

## 🛡️ Security & Bug Fix Highlights

1. **Privilege Escalation Prevention (Resolved)**:
   - Public registration route (`POST /api/v1/auth/register`) strictly forces `UserRole.farmer`.
   - The user registration payload schema (`UserRegister`) completely excludes the `role` field.
   - Admin accounts can only be provisioned through seed initialization or by authenticated super-admins via `POST /api/v1/admin/users`.
2. **Modern Bcrypt Engine**:
   - Replaced deprecated `passlib` with direct native `bcrypt` (`bcrypt.hashpw` / `bcrypt.checkpw`) to bypass the 72-byte string check bug on modern Python/Bcrypt versions.
3. **Anti-Spam Honeypot**:
   - Contact form & inquiry modals feature hidden honeypot fields (`hp_website` / `#contactHp`) that drop automated bot submissions before database storage.
4. **Rate Limiting & Security Headers**:
   - In-memory rate limiting applied to `/auth/login`, `/auth/register`, and `/leads`.
   - Production security headers configured: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `X-XSS-Protection: 1; mode=block`.

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.10+ (Tested on Python 3.11.9)
- MongoDB Atlas account (free tier works)
- Cloudinary account (optional; data-URI fallback operates automatically)

---

### Step 1 — Setup Backend

```bash
cd greenpulse/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### Step 2 — Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your MongoDB connection string and secret key:
```env
MONGODB_URL=mongodb+srv://<username>:<password>@cluster0.mongodb.net/greenpulse?retryWrites=true&w=majority
DB_NAME=greenpulse
SECRET_KEY=generate_a_random_64_char_key_here
ADMIN_EMAIL=admin@greenpulse.in
ADMIN_PASSWORD=Admin@123456
FRONTEND_URL=http://localhost:5500,http://127.0.0.1:5500
```

---

### Step 3 — Run Backend

```bash
uvicorn main:app --reload --port 8000
```

- Live API: `http://localhost:8000/api/v1`
- Swagger Interactive Docs: `http://localhost:8000/docs`
- Super-Admin Seed Account: `admin@greenpulse.in` / `Admin@123456`

---

### Step 4 — Run Frontend

```bash
cd greenpulse/frontend
python -m http.server 5500
```

- Homepage (Farmer Portal): `http://localhost:5500/`
- Admin Dashboard: `http://localhost:5500/admin.html`

---

## 🧪 Automated Testing

Run the integration test suite:

```bash
pytest greenpulse/backend/tests/test_api.py -v
```

Run frontend structure & link validation:

```bash
python greenpulse/backend/tests/verify_frontend.py
```

---

## 🔌 API Endpoints Reference

### 1. Authentication (`/api/v1/auth`)
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/register` | Public registration (Strictly `farmer`) | Public |
| POST | `/login` | Authenticate user, receive JWT token | Public |
| GET | `/me` | Get profile details of current user | Bearer Token |
| PUT | `/me` | Update farmer profile (name, village, land, crops) | Bearer Token |
| POST | `/change-password` | Change user password | Bearer Token |
| POST | `/logout` | Invalidate / clear session | Bearer Token |

### 2. Products (`/api/v1/products`)
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/` | List products with search, category & pagination | Public |
| GET | `/{id}` | Get single product details | Public |
| POST | `/` | Create new agriculture product | Admin |
| PUT | `/{id}` | Update product details | Admin |
| DELETE | `/{id}` | Delete product and associated Cloudinary images | Admin |
| POST | `/{id}/images` | Upload product images (Cloudinary) | Admin |
| DELETE | `/{id}/images` | Remove specific image from product | Admin |

### 3. Services (`/api/v1/services`)
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/` | List farm services (searchable) | Public |
| GET | `/{id}` | Get single service detail | Public |
| POST | `/` | Create new farm service | Admin |
| PUT | `/{id}` | Update farm service | Admin |
| DELETE | `/{id}` | Delete service | Admin |
| POST | `/{id}/images` | Upload service images | Admin |

### 4. Partners (`/api/v1/partners`)
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/` | List agricultural partner brands | Public |
| POST | `/` | Add partner brand | Admin |
| PUT | `/{id}` | Update partner information | Admin |
| DELETE | `/{id}` | Delete partner | Admin |
| POST | `/{id}/logo` | Upload partner brand logo | Admin |
| POST | `/{id}/images` | Upload partner gallery images | Admin |

### 5. Knowledge Center (`/api/v1/articles`)
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/` | List published articles (searchable) | Public |
| GET | `/{id}` | Read article (increments view count) | Public |
| POST | `/` | Publish new farming guide | Admin |
| PUT | `/{id}` | Edit article content | Admin |
| DELETE | `/{id}` | Delete article | Admin |
| POST | `/{id}/image` | Upload featured article image | Admin |

### 6. Leads & Inquiries (`/api/v1/leads`)
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/` | Submit callback request or message (Honeypot checked) | Public |
| GET | `/` | List all inquiries with filtering | Admin |
| GET | `/{id}` | View lead details | Admin |
| PUT | `/{id}/status` | Update lead status (`new`, `contacted`, `converted`) & notes | Admin |
| GET | `/export` | Export inquiries to UTF-8 BOM CSV for Excel | Admin |
| DELETE | `/{id}` | Delete inquiry | Admin |

### 7. Live Weather & Agricultural Advisories (`/api/v1/weather`)
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/` | Current weather, 7-day forecast & smart agri-advisories | Public |
| GET | `/search` | Search 30+ AP & Telangana agricultural mandals/villages | Public |

### 8. Admin Management (`/api/v1/admin`)
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/dashboard` | System statistics (counts, revenue, inquiries) | Admin |
| GET | `/public-settings` | Public website settings (phones, email, WhatsApp) | Public |
| GET / PUT | `/settings` | Update full platform settings | Admin |
| GET / POST | `/categories` | Dynamic category CRUD | Admin |
| GET / POST | `/testimonials` | Farmer testimonial CRUD | Admin |
| GET / POST | `/users` | User management & admin invitations | Admin |
| PUT | `/users/{id}/status`| Toggle user active/inactive status | Admin |

---

## ☁️ Deployment Guide

### Deploy Backend to Render

1. Create a new **Web Service** on [render.com](https://render.com).
2. Connect your repository.
3. Configure settings:
   - **Root Directory**: `greenpulse/backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Set Environment Variables in Render Dashboard:
   - `MONGODB_URL`: Your Atlas connection string
   - `DB_NAME`: `greenpulse`
   - `SECRET_KEY`: Long 64-char random hex key
   - `ADMIN_EMAIL`: `admin@greenpulse.in`
   - `ADMIN_PASSWORD`: Strong production password
   - `FRONTEND_URL`: Your Vercel frontend URL (e.g. `https://greenpulse.vercel.app`)
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`

---

### Deploy Frontend to Vercel

1. Import your Git repository into [vercel.com](https://vercel.com).
2. Set **Root Directory** to `greenpulse`.
3. Vercel automatically detects `vercel.json` with clean routing and security headers.
4. Click **Deploy**.

---

## 🌐 Telugu & English Bilingual Support

- The frontend features a toggle button: `🌐 తెలుగు / English`.
- Translates navigation, hero carousel, product actions, agricultural advisories, forms, and alerts dynamically without page reload.
- Remembers farmer language preference in `localStorage`.

---

*Built with 💚 for Indian Farmers — GreenPulse Platform © 2026*
