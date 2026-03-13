from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.routes.auth_routes import router as auth_router
from app.routes.user_routes import router as user_router
from app.routes.google_auth_routes import router as google_auth_router
from app.routes.security_routes import router as security_router
from app.routes.terms_routes import router as terms_router
from app.routes.district_routes import router as district_router

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="AquaSense API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─────────────────────────────────────────────
# CORS SETTINGS
# Controls which frontend origins are allowed to talk to this API
# During development we allow localhost ports used by Flutter
# In production replace these with your real app URLs
# ─────────────────────────────────────────────
origins = [
    "http://localhost:3000",        # React web app if needed
    "http://localhost:8081",        # Flutter web running locally
    "http://127.0.0.1:3000",        # Alternative localhost address
    "http://127.0.0.1:8081",        # Alternative localhost address
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# ROUTERS
# Each router handles a different section of the API
# ─────────────────────────────────────────────

# Handles /auth/register, /auth/login, /auth/logout etc
app.include_router(auth_router)

# Handles /user/profile, /user/update-profile, /user/delete-account
app.include_router(user_router)

# Handles /auth/google/login and /auth/google/callback
app.include_router(google_auth_router)

# Handles /security/settings, /security/2fa, /security/login-alerts etc
app.include_router(security_router)

# Handles /terms/check, /terms/status, /terms/save
app.include_router(terms_router)

# Handles /district/all, /district/my-district, /district/save
app.include_router(district_router)


# ─────────────────────────────────────────────
# GLOBAL EXCEPTION HANDLER
# Catches any unexpected errors that we did not handle ourselves
# Returns a clean JSON error instead of a Python traceback
# ─────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."}
    )


# ─────────────────────────────────────────────
# HEALTH CHECK
# Ping this to confirm the server is running
# ─────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "AquaSense API is running"}