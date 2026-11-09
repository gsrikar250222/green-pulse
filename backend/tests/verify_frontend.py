import re

with open("greenpulse/frontend/index.html", encoding="utf-8") as f:
    text = f.read()

checks = [
    ("BACKEND_URL", "BACKEND_URL" in text),
    ("farmerAuthModal", "farmerAuthModal" in text),
    ("productDetailModal", "productDetailModal" in text),
    ("serviceDetailModal", "serviceDetailModal" in text),
    ("articleReaderModal", "articleReaderModal" in text),
    ("inquiryModal", "inquiryModal" in text),
    ("toastContainer", "toastContainer" in text),
    ("productsGrid", 'id="productsGrid"' in text),
    ("servicesGrid", 'id="servicesGrid"' in text),
    ("partnersGrid", 'id="partnersGrid"' in text),
    ("articlesGrid", 'id="articlesGrid"' in text),
    ("testimonialsGrid", 'id="testimonialsGrid"' in text),
    ("weatherGrid", 'id="weatherGrid"' in text),
    ("weatherAdvisoriesContainer", 'id="weatherAdvisoriesContainer"' in text),
    ("contactHp (honeypot)", 'id="contactHp"' in text),
    ("contactSubmitBtn", 'id="contactSubmitBtn"' in text),
    ("galleryGrid (PhotoSwipe 5)", 'id="galleryGrid"' in text),
    ("services-swiper (Swiper 11)", 'services-swiper' in text),
    ("GSAP library CDN", 'gsap.min.js' in text),
    ("Swiper library CDN", 'swiper-bundle.min.js' in text),
    ("PhotoSwipe library CDN", 'photoswipe.umd.min.js' in text),
    ("Vanilla LazyLoad CDN", 'lazyload.min.js' in text),
    ("initPhotoSwipe", 'initPhotoSwipe' in text),
    ("initServicesSwiper", 'initServicesSwiper' in text),
    ("initGSAPAnimations", 'initGSAPAnimations' in text),
]

for name, res in checks:
    print(f"[{'PASS' if res else 'FAIL'}] {name}")

print("\n--- Checking admin.html ---")
with open("greenpulse/frontend/admin.html", encoding="utf-8") as f:
    admin_text = f.read()

admin_checks = [
    ("loginOverlay", "loginOverlay" in admin_text),
    ("productModal", 'id="productModal"' in admin_text),
    ("serviceModal", 'id="serviceModal"' in admin_text),
    ("partnerModal", 'id="partnerModal"' in admin_text),
    ("articleModal", 'id="articleModal"' in admin_text),
    ("leadModal", 'id="leadModal"' in admin_text),
    ("exportLeadsCSV", "exportLeadsCSV" in admin_text),
    ("handleAdminLogin", "handleAdminLogin" in admin_text),
    ("saveSettings", "saveSettings" in admin_text),
    ("editProduct", "editProduct" in admin_text),
    ("editService", "editService" in admin_text),
    ("editPartner", "editPartner" in admin_text),
    ("editArticle", "editArticle" in admin_text),
]

for name, res in admin_checks:
    print(f"[{'PASS' if res else 'FAIL'}] {name}")

