# app/main.py
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .database import Base, engine, SessionLocal
from . import models
from .routers import auth, billing, subscriptions, contact, welco, team, stats, live_chat, push
from .seed_data import COUNTRIES, SERVICE_PLANS

# Without this nothing below ERROR ever reaches Passenger's stderr.log, so the
# app's own logger.info calls (notably the per-message token/cache counters in
# welco_engine — the only way to tell prompt caching is still working) would go
# nowhere. Third-party libraries stay at WARNING so the log stays readable.
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("app").setLevel(logging.INFO)

# Táblák létrehozása (fejlesztéshez oké, később mehet alembic)
Base.metadata.create_all(bind=engine)


# Alapértelmezett szerepek biztosítása (idempotens): Admin, Client
def _seed_roles():
    db = SessionLocal()
    try:
        for name in ("Admin", "Client"):
            if not db.query(models.Role).filter(models.Role.Name == name).first():
                db.add(models.Role(Name=name))
        db.commit()
    finally:
        db.close()


# Orszag-tabla feltoltese (idempotens: csak ha ures)
def _seed_countries():
    db = SessionLocal()
    try:
        if db.query(models.Country).count() == 0:
            db.bulk_save_objects(
                [models.Country(Name=name, Code=code) for name, code in COUNTRIES]
            )
            db.commit()
    finally:
        db.close()


# Szolgaltatas-arkatalogus feltoltese (idempotens: csak ha ures)
def _seed_services():
    db = SessionLocal()
    try:
        if db.query(models.Service).count() == 0:
            db.bulk_save_objects([
                models.Service(
                    ServiceKey=key, ServiceName=name, Tier=tier,
                    MonthlyPrice=monthly, AnnualPrice=annual, SortOrder=order,
                    IsActive=True,
                )
                for key, name, tier, monthly, annual, order in SERVICE_PLANS
            ])
            db.commit()
    finally:
        db.close()


_seed_roles()
_seed_countries()
_seed_services()

app = FastAPI(
    title="WelcoChat API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"status": "ok"}


# Permissive CORS for the public widget API only — everything else on this
# API uses Bearer-JWT (no cookies), so this can't be used for a credentialed
# cross-site attack against the authenticated endpoints.
@app.middleware("http")
async def widget_cors(request: Request, call_next):
    if request.url.path.startswith("/widget/"):
        if request.method == "OPTIONS":
            response = Response(status_code=200)
        else:
            response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    return await call_next(request)


STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Auth router
app.include_router(auth.router, prefix="/auth", tags=["auth"])
# Billing router (countries + company)
app.include_router(billing.router, prefix="/billing", tags=["billing"])
# Subscriptions router
app.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
# Public contact router (kaptila.com landing form)
app.include_router(contact.router, tags=["contact"])
# WelcoChat: authenticated portal endpoints (activate/status)
app.include_router(welco.router, prefix="/welco", tags=["welco"])
# WelcoChat: public widget endpoints (no auth, CORS opened above)
app.include_router(welco.widget_router, prefix="/widget", tags=["welco-widget"])
# Team accounts (invite/manage members who share an owner's subscriptions)
app.include_router(team.router, prefix="/team", tags=["team"])
# Statistics (portal dashboard numbers, computed from existing usage tables)
app.include_router(stats.router, prefix="/stats", tags=["stats"])
# Live chat (portal-side reply into a Welco handoff conversation)
app.include_router(live_chat.router, prefix="/live-chat", tags=["live-chat"])

app.include_router(push.router, prefix="/push", tags=["push"])
