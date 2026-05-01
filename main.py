from fastapi import FastAPI, Request, Depends, Form, HTTPException, status, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
import models
from models import SessionLocal, engine, Achievement
import os
import shutil
from io import BytesIO
import extract_rab

# Database Seeding Logic
DATABASE_PATH = "./data/spm_am.db"
SEED_PATH = "./spm_am.db"

if not os.path.exists("./data"):
    os.makedirs("./data")

if not os.path.exists(DATABASE_PATH) or os.path.getsize(DATABASE_PATH) == 0:
    if os.path.exists(SEED_PATH) and os.path.getsize(SEED_PATH) > 0:
        shutil.copy2(SEED_PATH, DATABASE_PATH)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cianjur Tool Hub")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "spm-cianjur-secret-key-2026"))
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_current_user(request: Request):
    return request.session.get("user")

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
async def landing_hub(request: Request):
    if not get_current_user(request):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="landing.html")

@app.get("/spm", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request):
        return RedirectResponse(url="/login")
    
    items_raw = db.query(Achievement).all()
    grouped = {}
    for item in items_raw:
        key = (item.kecamatan, item.desa)
        if key not in grouped:
            grouped[key] = {"kecamatan": item.kecamatan, "desa": item.desa, "target": item.target, "total_sr": 0, "total_kk": 0, "years_list": []}
        grouped[key]["total_sr"] += (item.jumlah_sr or 0)
        grouped[key]["total_kk"] += (item.jumlah_kk or 0)
        grouped[key]["years_list"].append({"id": item.id, "tahun": item.tahun, "sr": item.jumlah_sr or 0, "kk": item.jumlah_kk or 0, "jiwa": item.jumlah_jiwa or 0})
        
    display_items = sorted(grouped.values(), key=lambda x: (x["kecamatan"], x["desa"]))
    total_sr = sum(item["total_sr"] for item in display_items)
    total_kk = sum(item["total_kk"] for item in display_items)
    total_target = sum(item["target"] for item in display_items)
    total_percentage = (total_kk / total_target * 100) if total_target > 0 else 0
    kecamatan_list = sorted(list(set([item.kecamatan for item in items_raw])))
    available_years = sorted(list(set([str(item.tahun) for item in items_raw])), reverse=True)
        
    return templates.TemplateResponse(request=request, name="index.html", context={
        "items": display_items, "total_sr": total_sr, "total_kk": total_kk, "total_target": total_target,
        "total_percentage": total_percentage, "kecamatan_list": kecamatan_list, "available_years": available_years
    })

@app.post("/add")
async def add_data(request: Request, kecamatan: str = Form(...), desa: str = Form(...), tahun: str = Form(...), jumlah_sr: int = Form(...), jumlah_kk: int = Form(...), db: Session = Depends(get_db)):
    if not get_current_user(request): return RedirectResponse(url="/login", status_code=302)
    existing = db.query(Achievement).filter(Achievement.desa == desa).first()
    target = existing.target if existing else 0
    new_item = Achievement(kecamatan=kecamatan, desa=desa, tahun=tahun, jumlah_sr=jumlah_sr, jumlah_kk=jumlah_kk, jumlah_jiwa=jumlah_kk*5, target=target, sumber_dana="Update Manual", program="Update Manual")
    db.add(new_item)
    db.commit()
    return RedirectResponse(url="/spm", status_code=303)

@app.post("/update/{item_id}")
async def update_item(request: Request, item_id: int, jumlah_sr: int = Form(...), jumlah_kk: int = Form(...), db: Session = Depends(get_db)):
    if not get_current_user(request): return RedirectResponse(url="/login", status_code=302)
    item = db.query(Achievement).filter(Achievement.id == item_id).first()
    if item:
        item.jumlah_sr = jumlah_sr
        item.jumlah_kk = jumlah_kk
        item.jumlah_jiwa = jumlah_kk * 5
        db.commit()
    return RedirectResponse(url="/spm", status_code=303)

# RAB ANALYZER ROUTES
@app.get("/rab", response_class=HTMLResponse)
async def rab_page(request: Request):
    if not get_current_user(request): return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="rab.html")

@app.post("/rab/analyze")
async def analyze_rab_post(request: Request, file: UploadFile = File(...)):
    if not get_current_user(request): return RedirectResponse(url="/login")
    content = await file.read()
    results = extract_rab.extract_rab(BytesIO(content))
    if not results: return {"status": "error", "message": "Gagal ekstrak data. Pastikan sheet bernama 'RAB'."}
    output_buffer = extract_rab.create_xlsx_buffer(results)
    filename = f"Analisa_RAB_{file.filename}"
    return StreamingResponse(output_buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
