from typing import List
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
from datetime import datetime
from models import RemiGame, RemiPlayer

# Database Seeding Logic
DATABASE_PATH = "./data/spm_am.db"
SEED_PATH = "./spm_am.db"

if not os.path.exists("./data"):
    os.makedirs("./data")

if not os.path.exists(DATABASE_PATH) or os.path.getsize(DATABASE_PATH) == 0:
    if os.path.exists(SEED_PATH) and os.path.getsize(SEED_PATH) > 0:
        shutil.copy2(SEED_PATH, DATABASE_PATH)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AMS Super APP")
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
async def analyze_rab_post(request: Request, files: List[UploadFile] = File(...)):
    if not get_current_user(request): return RedirectResponse(url="/login")
    
    all_results = []
    for file in files:
        content = await file.read()
        results = extract_rab.extract_rab(BytesIO(content))
        if results:
            all_results.extend(results)
            all_results.append({"item": "", "satuan": "", "volume": None, "harga": None, "pajak": "", "keterangan": "", "kunci": ""})
            
    if not all_results: 
        return {"status": "error", "message": "Gagal ekstrak data."}
        
    return {"status": "success", "data": all_results, "count": len(all_results)}

@app.post("/rab/download")
async def download_rab(request: Request):
    if not get_current_user(request): return RedirectResponse(url="/login")
    data = await request.json()
    output_buffer = extract_rab.create_xlsx_buffer(data)
    return StreamingResponse(output_buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=Analisa_Multi_RAB.xlsx"})

# REMI COUNTER ROUTES
@app.get("/remi", response_class=HTMLResponse)
async def remi_list(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request): return RedirectResponse(url="/login")
    games = db.query(RemiGame).order_by(RemiGame.created_at.desc()).all()
    
    # Hitung Juara Terbanyak (Top 3)
    from sqlalchemy import func
    top_winners = db.query(
        RemiGame.winner_name, 
        func.count(RemiGame.id).label('total_wins')
    ).filter(RemiGame.winner_name != None)\
     .group_by(RemiGame.winner_name)\
     .order_by(func.count(RemiGame.id).desc())\
     .limit(3).all()
     
    return templates.TemplateResponse(request=request, name="remi_list.html", context={
        "games": games,
        "top_winners": top_winners
    })

@app.post("/remi/{game_id}/delete")
async def remi_delete_game(request: Request, game_id: int, db: Session = Depends(get_db)):
    if not get_current_user(request): return RedirectResponse(url="/login")
    game = db.query(RemiGame).filter(RemiGame.id == game_id).first()
    if game:
        # Hapus pemainnya dulu (Cascading manual jika FK tidak di-set)
        db.query(RemiPlayer).filter(RemiPlayer.game_id == game_id).delete()
        db.query(RemiGame).filter(RemiGame.id == game_id).delete()
        db.commit()
    return RedirectResponse(url="/remi", status_code=303)

@app.post("/remi/new")
async def remi_new(request: Request, p1: str = Form(...), p2: str = Form(...), p3: str = Form(...), p4: str = Form(...), db: Session = Depends(get_db)):
    if not get_current_user(request): return RedirectResponse(url="/login")
    new_game = RemiGame(created_at=datetime.now().strftime("%Y-%m-%d %H:%M"))
    db.add(new_game)
    db.commit()
    db.refresh(new_game)
    
    for name in [p1, p2, p3, p4]:
        player = RemiPlayer(game_id=new_game.id, name=name, total_score=0)
        db.add(player)
    db.commit()
    return RedirectResponse(url=f"/remi/{new_game.id}", status_code=303)

@app.get("/remi/{game_id}", response_class=HTMLResponse)
async def remi_dashboard(request: Request, game_id: int, db: Session = Depends(get_db)):
    if not get_current_user(request): return RedirectResponse(url="/login")
    game = db.query(RemiGame).filter(RemiGame.id == game_id).first()
    players = db.query(RemiPlayer).filter(RemiPlayer.game_id == game_id).all()
    return templates.TemplateResponse(request=request, name="remi_game.html", context={"game": game, "players": players})

@app.post("/remi/{game_id}/update")
async def remi_update_score(request: Request, game_id: int, player_id: int = Form(...), added_points: int = Form(...), db: Session = Depends(get_db)):
    if not get_current_user(request): return RedirectResponse(url="/login")
    game = db.query(RemiGame).filter(RemiGame.id == game_id).first()
    if not game or not game.is_active: return RedirectResponse(url=f"/remi/{game_id}")
    
    player = db.query(RemiPlayer).filter(RemiPlayer.id == player_id).first()
    current_score = player.total_score
    new_score = current_score + added_points
    
    # Overtake Logic: Hanya berlaku jika pemain yang disalip skornya > 100
    others = db.query(RemiPlayer).filter(RemiPlayer.game_id == game_id, RemiPlayer.id != player_id).all()
    for other in others:
        # Jika skor lawan > 100 DAN kita berhasil melewati skor dia
        if other.total_score > 100 and current_score < other.total_score <= new_score:
            other.total_score = 0
            
    player.total_score = new_score
    if player.total_score >= 1000:
        game.is_active = 0
        game.winner_name = player.name
        
    db.commit()
    return RedirectResponse(url=f"/remi/{game_id}", status_code=303)

@app.post("/remi/{game_id}/round")
async def remi_update_round(request: Request, game_id: int, db: Session = Depends(get_db)):
    if not get_current_user(request): return RedirectResponse(url="/login")
    game = db.query(RemiGame).filter(RemiGame.id == game_id).first()
    if not game or not game.is_active: return RedirectResponse(url=f"/remi/{game_id}")
    
    form_data = await request.form()
    players = db.query(RemiPlayer).filter(RemiPlayer.game_id == game_id).all()
    
    # 1. Simpan skor lama untuk pengecekan overtake
    old_scores = {p.id: p.total_score for p in players}
    
    # 2. Update semua skor dulu
    for player in players:
        added_points = int(form_data.get(f"p_{player.id}") or 0)
        player.total_score += added_points

    # 3. Cek Overtake (Siapa menyalip siapa)
    # Aturan: Jika A_baru >= B_baru DAN A_lama < B_lama, maka B reset ke 0 (jika B_baru > 100)
    for p_a in players:
        for p_b in players:
            if p_a.id == p_b.id: continue
            
            # Jika Pemain A menyalip Pemain B
            if p_a.total_score >= p_b.total_score and old_scores[p_a.id] < old_scores[p_b.id]:
                if p_b.total_score > 100:
                    p_b.total_score = 0
    
    # 4. Cek Win Condition
    for player in players:
        if player.total_score >= 1000:
            game.is_active = 0
            game.winner_name = player.name
            break
            
    db.commit()
    return RedirectResponse(url=f"/remi/{game_id}", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
