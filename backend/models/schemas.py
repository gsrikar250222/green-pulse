"""
GreenPulse – Pydantic schemas for all collections
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


# ────────────────────────────────────────────
#  ENUMS
# ────────────────────────────────────────────

class UserRole(str, Enum):
    admin   = "admin"
    farmer  = "farmer"
    partner = "partner"
    company = "company"


class LeadType(str, Enum):
    product  = "product"
    service  = "service"
    callback = "callback"
    contact  = "contact"


class LeadStatus(str, Enum):
    new        = "new"
    contacted  = "contacted"
    converted  = "converted"
    closed     = "closed"


class CategoryType(str, Enum):
    product  = "product"
    service  = "service"
    article  = "article"


# ────────────────────────────────────────────
#  AUTH
# ────────────────────────────────────────────

class UserRegister(BaseModel):
    name:     str = Field(..., min_length=2, max_length=100)
    email:    EmailStr
    password: str = Field(..., min_length=6)
    phone:    Optional[str] = None
    village:  Optional[str] = None
    crop:     Optional[str] = None


class UserCreate(BaseModel):
    name:     str = Field(..., min_length=2, max_length=100)
    email:    EmailStr
    password: str = Field(..., min_length=6)
    role:     UserRole = UserRole.farmer
    phone:    Optional[str] = None
    village:  Optional[str] = None
    crop:     Optional[str] = None


class UserLogin(BaseModel):
    email:    EmailStr
    password: str


class UserProfileUpdate(BaseModel):
    name:     Optional[str] = Field(None, min_length=2, max_length=100)
    phone:    Optional[str] = None
    village:  Optional[str] = None
    crop:     Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class UserOut(BaseModel):
    id:         str
    name:       str
    email:      str
    role:       UserRole
    phone:      Optional[str] = None
    village:    Optional[str] = None
    crop:       Optional[str] = None
    is_active:  bool = True
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserOut


# ────────────────────────────────────────────
#  PRODUCTS
# ────────────────────────────────────────────

class ProductCreate(BaseModel):
    name:           str = Field(..., min_length=2, max_length=200)
    description:    str
    category:       str
    sub_category:   Optional[str] = None
    brand:          Optional[str] = None
    tags:           List[str] = []
    is_active:      bool = True
    is_featured:    bool = False
    brochure_url:   Optional[str] = None
    whatsapp_msg:   Optional[str] = None


class ProductUpdate(BaseModel):
    name:           Optional[str] = None
    description:    Optional[str] = None
    category:       Optional[str] = None
    sub_category:   Optional[str] = None
    brand:          Optional[str] = None
    tags:           Optional[List[str]] = None
    is_active:      Optional[bool] = None
    is_featured:    Optional[bool] = None
    brochure_url:   Optional[str] = None
    whatsapp_msg:   Optional[str] = None


class ProductOut(BaseModel):
    id:             str
    name:           str
    description:    str
    category:       str
    sub_category:   Optional[str]
    brand:          Optional[str]
    tags:           List[str]
    images:         List[str]
    is_active:      bool
    is_featured:    bool
    brochure_url:   Optional[str]
    whatsapp_msg:   Optional[str]
    created_at:     datetime
    updated_at:     Optional[datetime]


# ────────────────────────────────────────────
#  SERVICES
# ────────────────────────────────────────────

class ServiceCreate(BaseModel):
    name:        str = Field(..., min_length=2, max_length=200)
    description: str
    category:    str
    details:     Optional[str] = None
    tags:        List[str] = []
    is_active:   bool = True
    is_featured: bool = False


class ServiceUpdate(BaseModel):
    name:        Optional[str] = None
    description: Optional[str] = None
    category:    Optional[str] = None
    details:     Optional[str] = None
    tags:        Optional[List[str]] = None
    is_active:   Optional[bool] = None
    is_featured: Optional[bool] = None


class ServiceOut(BaseModel):
    id:          str
    name:        str
    description: str
    category:    str
    details:     Optional[str]
    tags:        List[str]
    images:      List[str]
    is_active:   bool
    is_featured: bool
    created_at:  datetime


# ────────────────────────────────────────────
#  PARTNERS
# ────────────────────────────────────────────

class PartnerCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=200)
    description:  str
    category:     Optional[str] = None
    website:      Optional[str] = None
    email:        Optional[EmailStr] = None
    phone:        Optional[str] = None
    address:      Optional[str] = None
    is_active:    bool = True
    is_featured:  bool = False


class PartnerUpdate(BaseModel):
    company_name: Optional[str] = None
    description:  Optional[str] = None
    category:     Optional[str] = None
    website:      Optional[str] = None
    email:        Optional[EmailStr] = None
    phone:        Optional[str] = None
    address:      Optional[str] = None
    is_active:    Optional[bool] = None
    is_featured:  Optional[bool] = None


class PartnerOut(BaseModel):
    id:           str
    company_name: str
    description:  str
    category:     Optional[str]
    website:      Optional[str]
    email:        Optional[str]
    phone:        Optional[str]
    address:      Optional[str]
    logo_url:     Optional[str]
    images:       List[str]
    is_active:    bool
    is_featured:  bool
    created_at:   datetime


# ────────────────────────────────────────────
#  KNOWLEDGE ARTICLES
# ────────────────────────────────────────────

class ArticleCreate(BaseModel):
    title:        str = Field(..., min_length=5, max_length=300)
    content:      str
    excerpt:      Optional[str] = None
    category:     str
    tags:         List[str] = []
    author_name:  Optional[str] = "GreenPulse Team"
    is_published: bool = False
    is_featured:  bool = False


class ArticleUpdate(BaseModel):
    title:        Optional[str] = None
    content:      Optional[str] = None
    excerpt:      Optional[str] = None
    category:     Optional[str] = None
    tags:         Optional[List[str]] = None
    author_name:  Optional[str] = None
    is_published: Optional[bool] = None
    is_featured:  Optional[bool] = None


class ArticleOut(BaseModel):
    id:            str
    title:         str
    content:       str
    excerpt:       Optional[str]
    category:      str
    tags:          List[str]
    author_name:   str
    featured_image:Optional[str]
    is_published:  bool
    is_featured:   bool
    views:         int
    created_at:    datetime
    updated_at:    Optional[datetime]


# ────────────────────────────────────────────
#  LEADS / INQUIRIES
# ────────────────────────────────────────────

class LeadCreate(BaseModel):
    name:        str = Field(..., min_length=2, max_length=100)
    phone:       str = Field(..., min_length=10, max_length=15)
    email:       Optional[EmailStr] = None
    village:     Optional[str] = None
    crop:        Optional[str] = None
    message:     Optional[str] = None
    type:        LeadType = LeadType.contact
    product_id:  Optional[str] = None
    service_id:  Optional[str] = None
    source:      Optional[str] = "website"
    hp_website:  Optional[str] = None  # Honeypot field for bot spam detection


class LeadStatusUpdate(BaseModel):
    status: LeadStatus
    notes:  Optional[str] = None


class LeadOut(BaseModel):
    id:         str
    name:       str
    phone:      str
    email:      Optional[str]
    village:    Optional[str]
    crop:       Optional[str]
    message:    Optional[str]
    type:       LeadType
    status:     LeadStatus
    product_id: Optional[str]
    service_id: Optional[str]
    source:     Optional[str]
    notes:      Optional[str]
    created_at: datetime


# ────────────────────────────────────────────
#  CATEGORIES
# ────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name:  str = Field(..., min_length=2, max_length=100)
    slug:  str = Field(..., min_length=2, max_length=100)
    type:  CategoryType
    icon:  Optional[str] = None
    order: int = 0


class CategoryUpdate(BaseModel):
    name:  Optional[str] = None
    slug:  Optional[str] = None
    type:  Optional[CategoryType] = None
    icon:  Optional[str] = None
    order: Optional[int] = None


class CategoryOut(BaseModel):
    id:    str
    name:  str
    slug:  str
    type:  CategoryType
    icon:  Optional[str]
    order: int


# ────────────────────────────────────────────
#  TESTIMONIALS
# ────────────────────────────────────────────

class TestimonialCreate(BaseModel):
    name:      str
    location:  str
    text:      str
    rating:    int = Field(5, ge=1, le=5)
    crop_type: Optional[str] = None
    is_active: bool = True


class TestimonialUpdate(BaseModel):
    name:      Optional[str] = None
    location:  Optional[str] = None
    text:      Optional[str] = None
    rating:    Optional[int] = Field(None, ge=1, le=5)
    crop_type: Optional[str] = None
    is_active: Optional[bool] = None


class TestimonialOut(BaseModel):
    id:        str
    name:      str
    location:  str
    text:      str
    rating:    int
    crop_type: Optional[str]
    photo_url: Optional[str]
    is_active: bool
    created_at:datetime


# ────────────────────────────────────────────
#  SITE SETTINGS
# ────────────────────────────────────────────

class SiteSettingsUpdate(BaseModel):
    site_name:       Optional[str] = None
    tagline:         Optional[str] = None
    contact_phone:   Optional[str] = None
    contact_email:   Optional[str] = None
    contact_address: Optional[str] = None
    whatsapp_number: Optional[str] = None
    facebook_url:    Optional[str] = None
    instagram_url:   Optional[str] = None
    twitter_url:     Optional[str] = None
    meta_title:      Optional[str] = None
    meta_description:Optional[str] = None


# ────────────────────────────────────────────
#  GENERIC
# ────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items:   List[Any]
    total:   int
    page:    int
    limit:   int
    pages:   int


class MessageResponse(BaseModel):
    message: str
    success: bool = True
