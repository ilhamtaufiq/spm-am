from sqlalchemy import func
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
from models import RemiGame, RemiPlayer, RemiRound

# Database Seeding Logic
DATABASE_PATH = "./data/spm_am.db"
SEED_PATH = "./spm_am.db"

if not os.path.exists("./data"):
    os.makedirs("./data")

if not os.path.exists(DATABASE_PATH) or os.path.getsize(DATABASE_PATH) == 0:
    if os.path.exists(SEED_PATH) and os.path.getsize(SEED_PATH) > 0:
        import shutil
        shutil.copy2(SEED_PATH, DATABASE_PATH)


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AMS Super APP")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "spm-cianjur-secret-key-2026"))
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def load_bjp_data():
    bjp_data = {}
    if os.path.exists("semua_desa.md"):
        with open("semua_desa.md", "r") as f:
            for line in f:
                parts = [p.strip() for p in line.split('\t') if p.strip()]
                if len(parts) >= 3:
                    kec = parts[0].upper()
                    desa = parts[1].upper()
                    try:
                        kk = int(parts[2].replace(',', '').replace('.', ''))
                        bjp_data[(kec, desa)] = kk
                    except:
                        pass
    return bjp_data

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
    
    bjp_map = load_bjp_data()
    items_raw = db.query(Achievement).all()
    grouped = {}
    for item in items_raw:
        key = (item.kecamatan.upper(), item.desa.upper())
        if key not in grouped:
            # Use DB value if exists and not zero, otherwise fallback to .md file
            bjp_kk = item.jumlah_bjp_kk if (item.jumlah_bjp_kk and item.jumlah_bjp_kk > 0) else bjp_map.get(key, 0)
            grouped[key] = {
                "kecamatan": item.kecamatan, 
                "desa": item.desa, 
                "target": item.target, 
                "total_sr": 0, "total_kk": 0, 
                "total_bjp_kk": 0, # We'll sum this up
                "years_list": []
            }
        
        # Fallback logic for BJP in each year row
        bjp_kk_row = item.jumlah_bjp_kk if (item.jumlah_bjp_kk and item.jumlah_bjp_kk > 0) else bjp_map.get(key, 0)
        
        grouped[key]["total_sr"] += (item.jumlah_sr or 0)
        grouped[key]["total_kk"] += (item.jumlah_kk or 0)
        grouped[key]["total_bjp_kk"] += (item.jumlah_bjp_kk or 0) # Real sum from DB
        grouped[key]["years_list"].append({
            "id": item.id, "tahun": item.tahun, 
            "sr": item.jumlah_sr or 0, "kk": item.jumlah_kk or 0, "jiwa": item.jumlah_jiwa or 0,
            "bjp_kk": bjp_kk_row, "bjp_jiwa": (bjp_kk_row * 5),
            "meta": {
                "sumber_dana": item.sumber_dana, "program": item.program,
                "sistem_layanan": item.sistem_layanan, "kepala": item.kepala,
                "iuran_nominal": item.iuran_nominal, "biaya_operasional": item.biaya_operasional,
                "pokmas": item.pokmas, "perdes": item.perdes,
                "bendahara": item.bendahara, "sekretaris": item.sekretaris,
                "sumber_mata_air_kap": item.sumber_mata_air_kap,
                "sumber_air_tanah_kap": item.sumber_air_tanah_kap,
                "lain_lain_kap": item.lain_lain_kap,
                "tarif_dasar_hukum": item.tarif_dasar_hukum,
                "catatan": item.catatan
            }
        })
        
    for key, data in grouped.items():
        # If total_bjp_kk is still 0 across all years, use the .md fallback for the summary
        if data["total_bjp_kk"] == 0:
            data["bjp_kk"] = bjp_map.get(key, 0)
        else:
            data["bjp_kk"] = data["total_bjp_kk"]
        data["bjp_jiwa"] = data["bjp_kk"] * 5

    display_items = sorted(grouped.values(), key=lambda x: (x["kecamatan"], x["desa"]))
    
    # Calculate Totals
    total_sr = sum(item["total_sr"] for item in display_items)
    total_kk = sum(item["total_kk"] for item in display_items)
    total_bjp_kk = sum(item["bjp_kk"] for item in display_items)
    total_target = sum(item["target"] for item in display_items)
    
    total_percentage = (total_kk / total_target * 100) if total_target > 0 else 0
    total_bjp_percentage = (total_bjp_kk / total_target * 100) if total_target > 0 else 0
    total_combined_percentage = ((total_kk + total_bjp_kk) / total_target * 100) if total_target > 0 else 0
    
    kecamatan_list = sorted(list(set([item.kecamatan for item in items_raw])))
    available_years = sorted(list(set([str(item.tahun) for item in items_raw])), reverse=True)
        
    return templates.TemplateResponse(request=request, name="index.html", context={
        "items": display_items, 
        "total_sr": total_sr, 
        "total_kk": total_kk, 
        "total_bjp_kk": total_bjp_kk,
        "total_target": total_target,
        "total_percentage": total_percentage, 
        "total_bjp_percentage": total_bjp_percentage,
        "total_combined_percentage": total_combined_percentage,
        "kecamatan_list": kecamatan_list, 
        "available_years": available_years
    })

@app.post("/add")
async def add_data(
    request: Request, 
    kecamatan: str = Form(...), 
    desa: str = Form(...), 
    tahun: str = Form(...), 
    jumlah_sr: int = Form(...), 
    jumlah_kk: int = Form(...), 
    jumlah_bjp_kk: int = Form(0),
    pokmas: str = Form(None),
    perdes: str = Form(None),
    kepala: str = Form(None),
    bendahara: str = Form(None),
    sekretaris: str = Form(None),
    sumber_mata_air_kap: str = Form(None),
    sistem_layanan: str = Form(None),
    sumber_air_tanah_kap: str = Form(None),
    lain_lain_kap: str = Form(None),
    tarif_dasar_hukum: str = Form(None),
    iuran_nominal: str = Form(None),
    biaya_operasional: str = Form(None),
    sumber_dana: str = Form("Manual"),
    program: str = Form("Manual"),
    catatan: str = Form(None),
    db: Session = Depends(get_db)
):
    if not get_current_user(request): return RedirectResponse(url="/login", status_code=302)
    existing = db.query(Achievement).filter(Achievement.desa == desa).first()
    target = existing.target if existing else 0
    new_item = Achievement(
        kecamatan=kecamatan, desa=desa, tahun=tahun, 
        jumlah_sr=jumlah_sr, jumlah_kk=jumlah_kk, jumlah_jiwa=jumlah_kk*5, 
        jumlah_bjp_kk=jumlah_bjp_kk, jumlah_bjp_jiwa=jumlah_bjp_kk*5,
        target=target, pokmas=pokmas, perdes=perdes, kepala=kepala,
        bendahara=bendahara, sekretaris=sekretaris,
        sumber_mata_air_kap=sumber_mata_air_kap, sistem_layanan=sistem_layanan,
        sumber_air_tanah_kap=sumber_air_tanah_kap, lain_lain_kap=lain_lain_kap,
        tarif_dasar_hukum=tarif_dasar_hukum, iuran_nominal=iuran_nominal,
        biaya_operasional=biaya_operasional, sumber_dana=sumber_dana,
        program=program, catatan=catatan
    )
    db.add(new_item)
    db.commit()
    return RedirectResponse(url="/spm", status_code=303)

@app.post("/update/{item_id}")
async def update_item(
    request: Request, 
    item_id: int, 
    jumlah_sr: int = Form(...), 
    jumlah_kk: int = Form(...), 
    jumlah_bjp_kk: int = Form(0), 
    pokmas: str = Form(None),
    perdes: str = Form(None),
    kepala: str = Form(None),
    bendahara: str = Form(None),
    sekretaris: str = Form(None),
    sumber_mata_air_kap: str = Form(None),
    sistem_layanan: str = Form(None),
    sumber_air_tanah_kap: str = Form(None),
    lain_lain_kap: str = Form(None),
    tarif_dasar_hukum: str = Form(None),
    iuran_nominal: str = Form(None),
    biaya_operasional: str = Form(None),
    sumber_dana: str = Form(None),
    program: str = Form(None),
    catatan: str = Form(None),
    db: Session = Depends(get_db)
):
    if not get_current_user(request): return RedirectResponse(url="/login", status_code=302)
    item = db.query(Achievement).filter(Achievement.id == item_id).first()
    if item:
        item.jumlah_sr = jumlah_sr
        item.jumlah_kk = jumlah_kk
        item.jumlah_jiwa = jumlah_kk * 5
        item.jumlah_bjp_kk = jumlah_bjp_kk
        item.jumlah_bjp_jiwa = jumlah_bjp_kk * 5
        item.pokmas = pokmas
        item.perdes = perdes
        item.kepala = kepala
        item.bendahara = bendahara
        item.sekretaris = sekretaris
        item.sumber_mata_air_kap = sumber_mata_air_kap
        item.sistem_layanan = sistem_layanan
        item.sumber_air_tanah_kap = sumber_air_tanah_kap
        item.lain_lain_kap = lain_lain_kap
        item.tarif_dasar_hukum = tarif_dasar_hukum
        item.iuran_nominal = iuran_nominal
        item.biaya_operasional = biaya_operasional
        item.sumber_dana = sumber_dana
        item.program = program
        item.catatan = catatan
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
    
    # Get round history
    rounds_raw = db.query(RemiRound).filter(RemiRound.game_id == game_id).order_by(RemiRound.round_number.desc(), RemiRound.id.asc()).all()
    
    # Group rounds for display: {round_num: {player_id: points}}
    history = {}
    for r in rounds_raw:
        if r.round_number not in history:
            history[r.round_number] = {}
        history[r.round_number][r.player_id] = r.points
        
    return templates.TemplateResponse(request=request, name="remi_game.html", context={
        "game": game, 
        "players": players,
        "history": history
    })


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
    
    # 0. Get current round number
    last_round = db.query(func.max(RemiRound.round_number)).filter(RemiRound.game_id == game_id).scalar() or 0
    current_round = last_round + 1
    
    # 1. Simpan skor lama untuk pengecekan overtake
    old_scores = {p.id: p.total_score for p in players}
    
    # 2. Update semua skor dulu dan simpan history
    for player in players:
        added_points = int(form_data.get(f"p_{player.id}") or 0)
        player.total_score += added_points
        
        # Save round history
        round_entry = RemiRound(game_id=game_id, player_id=player.id, points=added_points, round_number=current_round)
        db.add(round_entry)

    # 3. Cek Overtake (Siapa menyalip siapa)
    for p_a in players:
        for p_b in players:
            if p_a.id == p_b.id: continue
            
            # Jika Pemain A menyalip Pemain B
            if p_a.total_score >= p_b.total_score and old_scores[p_a.id] < old_scores[p_b.id]:
                if p_b.total_score > 100:
                    # Save a special history entry for the reset
                    # points = -p_b.total_score (to make it 0)
                    reset_points = -p_b.total_score
                    p_b.total_score = 0
                    
                    # We add another history entry for the reset event
                    # We can use a decimal round number or just the same round number
                    reset_entry = RemiRound(game_id=game_id, player_id=p_b.id, points=reset_points, round_number=current_round)
                    db.add(reset_entry)
    
    # 4. Cek Win Condition
    for player in players:
        if player.total_score >= 1000:
            game.is_active = 0
            game.winner_name = player.name
            break
            
    db.commit()
    return RedirectResponse(url=f"/remi/{game_id}", status_code=303)




@app.post("/api/bulk-update-catatan")
async def bulk_update_catatan(
    request: Request,
    db: Session = Depends(get_db)
):
    if not get_current_user(request): 
        return {"status": "error", "message": "Unauthorized"}
    
    data = await request.json()
    village_names = data.get("villages", [])
    new_note = data.get("catatan", "")
    target_year = data.get("year", "All")
    
    if not village_names:
        return {"status": "error", "message": "No villages selected"}
        
    if target_year != "All":
        from models import Achievement
        db.query(Achievement).filter(
            Achievement.desa.in_(village_names),
            Achievement.tahun == target_year
        ).update({"catatan": new_note}, synchronize_session=False)
    else:
        from models import Achievement
        # Update latest record for each village
        for v_name in village_names:
            latest = db.query(Achievement).filter(Achievement.desa == v_name).order_by(Achievement.tahun.desc()).first()
            if latest:
                latest.catatan = new_note
                
    db.commit()
    return {"status": "success", "message": f"Berhasil update {len(village_names)} data."}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
