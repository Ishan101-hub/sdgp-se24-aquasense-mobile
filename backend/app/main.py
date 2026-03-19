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
# allow_origins=["*"] allows Chrome browser and any frontend to connect
# allow_credentials must be False when using ["*"]
# Change this to specific origins before going to production
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # allows Chrome, Flutter web, any origin
    allow_credentials=False,    # must be False when allow_origins is ["*"]
    allow_methods=["*"],        # allows GET, POST, PUT, DELETE etc
    allow_headers=["*"],        # allows Authorization, Content-Type etc
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