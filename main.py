from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
import models
from models import SessionLocal, engine, Achievement
import os
import shutil

# Database Seeding Logic
DATABASE_PATH = "./data/spm_am.db"
SEED_PATH = "./spm_am.db"

if not os.path.exists("./data"):
    os.makedirs("./data")

# Jika file di folder data tidak ada atau ukurannya 0 (kosong), copy dari seed
if not os.path.exists(DATABASE_PATH) or os.path.getsize(DATABASE_PATH) == 0:
    if os.path.exists(SEED_PATH) and os.path.getsize(SEED_PATH) > 0:
        print(f"Seeding database from {SEED_PATH} to {DATABASE_PATH}")
        shutil.copy2(SEED_PATH, DATABASE_PATH)

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SPM Air Minum Cianjur")
# Gunakan secret key dari env jika ada
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "spm-cianjur-secret-key-2026"))

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Auth Helpers
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return None
    return user

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "cianjur2026":
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": "Username atau Password salah!"})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    items_raw = db.query(Achievement).all()
    # Group items by (kecamatan, desa)
    grouped = {}
    total_sr = 0
    total_kk = 0
    total_target = 0
    
    for item in items_raw:
        key = (item.kecamatan, item.desa)
        if key not in grouped:
            grouped[key] = {
                "kecamatan": item.kecamatan,
                "desa": item.desa,
                "target": item.target,
                "total_sr": 0,
                "total_kk": 0,
                "years_list": [] # For Detail view
            }
        
        # Add to totals
        grouped[key]["total_sr"] += (item.jumlah_sr or 0)
        grouped[key]["total_kk"] += (item.jumlah_kk or 0)
        
        # Add to years list
        grouped[key]["years_list"].append({
            "id": item.id,
            "tahun": item.tahun,
            "sr": item.jumlah_sr or 0,
            "kk": item.jumlah_kk or 0,
            "jiwa": item.jumlah_jiwa or 0,
            "meta": {c.name: getattr(item, c.name) for c in item.__table__.columns if c.name not in ['id', 'kecamatan', 'desa', 'tahun']}
        })
        
    # Convert to list and sort by kecamatan, desa
    display_items = sorted(grouped.values(), key=lambda x: (x["kecamatan"], x["desa"]))
    
    # Calculate global totals accurately (avoid double-counting targets)
    total_sr = sum(item["total_sr"] for item in display_items)
    total_kk = sum(item["total_kk"] for item in display_items)
    total_target = sum(item["target"] for item in display_items)
    
    total_percentage = (total_kk / total_target * 100) if total_target > 0 else 0
    kecamatan_list = sorted(list(set([item.kecamatan for item in items_raw])))
    available_years = sorted(list(set([str(item.tahun) for item in items_raw])), reverse=True)
        
    return templates.TemplateResponse(request=request, name="index.html", context={
        "items": display_items,
        "total_sr": total_sr,
        "total_kk": total_kk,
        "total_target": total_target,
        "total_percentage": total_percentage,
        "kecamatan_list": kecamatan_list,
        "available_years": available_years
    })

@app.get("/edit/{item_id}", response_class=HTMLResponse)
async def edit_item(request: Request, item_id: int, db: Session = Depends(get_db)):
    item = db.query(Achievement).filter(Achievement.id == item_id).first()
    return templates.TemplateResponse(request=request, name="edit.html", context={"item": item})

@app.get("/api/kecamatan")
async def get_kecamatans(db: Session = Depends(get_db)):
    res = db.query(Achievement.kecamatan).distinct().all()
    return [r[0] for r in res if r[0]]

@app.get("/api/desa/{kecamatan}")
async def get_desas(kecamatan: str, db: Session = Depends(get_db)):
    res = db.query(Achievement.desa).filter(Achievement.kecamatan == kecamatan).distinct().all()
    return [r[0] for r in res if r[0]]

@app.get("/api/tahun/{kecamatan}/{desa}")
async def get_tahuns(kecamatan: str, desa: str, db: Session = Depends(get_db)):
    res = db.query(Achievement.tahun).filter(
        Achievement.kecamatan == kecamatan, 
        Achievement.desa == desa
    ).distinct().all()
    return [r[0] for r in res if r[0]]

@app.get("/api/desa/{kecamatan}")
async def get_desa(kecamatan: str, db: Session = Depends(get_db)):
    res = db.query(Achievement.desa).filter(Achievement.kecamatan == kecamatan).distinct().all()
    return sorted([r[0] for r in res if r[0]])

@app.post("/add")
async def add_data(
    request: Request,
    kecamatan: str = Form(...),
    desa: str = Form(...),
    tahun: str = Form(...),
    jumlah_sr: int = Form(...),
    jumlah_kk: int = Form(...),
    db: Session = Depends(get_db)
):
    if not get_current_user(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    # Check if target exists for this village to copy it
    existing = db.query(Achievement).filter(Achievement.desa == desa).first()
    target = existing.target if existing else 0
    
    new_item = Achievement(
        kecamatan=kecamatan,
        desa=desa,
        tahun=tahun,
        jumlah_sr=jumlah_sr,
        jumlah_kk=jumlah_kk,
        target=target,
        sumber_dana="Update Manual",
        program="Update Manual"
    )
    db.add(new_item)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/api/update-v2")
async def update_v2(
    request: Request,
    kecamatan: str = Form(...),
    desa: str = Form(...),
    tahun: str = Form(...),
    jumlah_sr: int = Form(...),
    db: Session = Depends(get_db)
):
    if not get_current_user(request):
        return {"status": "error", "message": "Unauthorized"}
    item = db.query(Achievement).filter(
        Achievement.kecamatan == kecamatan,
        Achievement.desa == desa,
        Achievement.tahun == tahun
    ).first()
    
    if item:
        item.jumlah_sr = jumlah_sr
        db.commit()
        return {"status": "success", "message": "Data updated"}
    return {"status": "error", "message": "Record not found"}

@app.post("/update/{item_id}")
async def update_item(
    request: Request,
    item_id: int, 
    jumlah_sr: int = Form(...),
    jumlah_kk: int = Form(...),
    jumlah_jiwa: int = Form(...),
    db: Session = Depends(get_db)
):
    if not get_current_user(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    item = db.query(Achievement).filter(Achievement.id == item_id).first()
    if item:
        item.jumlah_sr = jumlah_sr
        item.jumlah_kk = jumlah_kk
        item.jumlah_jiwa = jumlah_jiwa
        db.commit()
    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
