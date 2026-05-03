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
                    kec = parts[0].strip().upper()
                    desa = parts[1].strip().upper().replace(' ', '')
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
    
    # Query UnitSpam and join Desa, Kecamatan, Pengelola
    units = db.query(models.UnitSpam).join(models.Desa).join(models.Kecamatan).all()
    
    bjp_file_map = load_bjp_data()
    
    display_items = []
    for u in units:
        # Sum annual achievements
        total_sr = sum(a.jumlah_sr or 0 for a in u.achievements)
        total_kk = sum(a.jumlah_kk or 0 for a in u.achievements)
        
        # BJP from file (master) + BJP from achievements (new)
        file_bjp = bjp_file_map.get((u.desa.kecamatan.name, u.desa.name), 0)
        total_bjp_kk = file_bjp + sum(a.jumlah_bjp_kk or 0 for a in u.achievements)
        
        # Sort years descending
        years_list = sorted([
            {
                "id": a.id, "tahun": a.tahun,
                "sr": a.jumlah_sr or 0, "kk": a.jumlah_kk or 0, "jiwa": a.jumlah_jiwa or 0,
                "bjp_kk": a.jumlah_bjp_kk or 0, "bjp_jiwa": a.jumlah_bjp_jiwa or 0,
                "meta": {
                    "sumber_dana": u.sumber_dana, "program": u.program,
                    "sistem_layanan": u.sistem_layanan, "kepala": u.pengelola.kepala if u.pengelola else "",
                    "iuran_nominal": u.iuran_nominal, "biaya_operasional": u.biaya_operasional,
                    "pokmas": u.pengelola.pokmas if u.pengelola else "", 
                    "perdes": u.pengelola.perdes if u.pengelola else "",
                    "bendahara": u.pengelola.bendahara if u.pengelola else "", 
                    "sekretaris": u.pengelola.sekretaris if u.pengelola else "",
                    "sumber_mata_air_kap": u.sumber_mata_air_kap,
                    "sumber_air_tanah_kap": u.sumber_air_tanah_kap,
                    "lain_lain_kap": u.lain_lain_kap,
                    "tarif_dasar_hukum": u.tarif_dasar_hukum,
                    "catatan": a.catatan
                }
            } for a in u.achievements
        ], key=lambda x: x["tahun"], reverse=True)
        
        display_items.append({
            "unit_id": u.id,
            "kecamatan": u.desa.kecamatan.name,
            "desa": u.desa.name,
            "is_simspam": u.is_simspam,
            "target": u.desa.target,
            "total_sr": total_sr,
            "total_kk": total_kk,
            "bjp_kk": total_bjp_kk,
            "bjp_jiwa": total_bjp_kk * 5,
            "years_list": years_list
        })

    display_items = sorted(display_items, key=lambda x: (x["kecamatan"], x["desa"]))
    
    # Calculate Grand Totals
    grand_total_sr = sum(item["total_sr"] for item in display_items)
    grand_total_kk = sum(item["total_kk"] for item in display_items)
    # Total BJP is sum of all file-based BJP + sum of all achievement-based BJP
    total_bjp_file = sum(bjp_file_map.values())
    total_bjp_db = db.query(func.sum(models.Achievement.jumlah_bjp_kk)).scalar() or 0
    grand_total_bjp_kk = total_bjp_file + total_bjp_db
    
    # Target should be sum of ALL villages in the kabupaten
    grand_total_target = db.query(func.sum(models.Desa.target)).scalar() or 0
    
    total_combined_percentage = ((grand_total_kk + grand_total_bjp_kk) / grand_total_target * 100) if grand_total_target > 0 else 0
    
    kecamatan_list = sorted([k.name for k in db.query(models.Kecamatan).all()])
    available_years = sorted(list(set([str(a.tahun) for a in db.query(models.Achievement).all()])), reverse=True)
        
    return templates.TemplateResponse(request=request, name="index.html", context={
        "items": display_items, 
        "total_sr": grand_total_sr, 
        "total_kk": grand_total_kk, 
        "total_bjp_kk": grand_total_bjp_kk,
        "total_target": grand_total_target,
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
    
    # Normalize inputs
    kec_name = kecamatan.upper()
    desa_name = desa.upper().replace(" ", "")
    
    # 1. Get/Create Kecamatan
    kec = db.query(models.Kecamatan).filter(models.Kecamatan.name == kec_name).first()
    if not kec:
        kec = models.Kecamatan(name=kec_name)
        db.add(kec)
        db.flush()
        
    # 2. Get/Create Desa
    d_obj = db.query(models.Desa).filter(models.Desa.kecamatan_id == kec.id, models.Desa.name == desa_name).first()
    if not d_obj:
        d_obj = models.Desa(kecamatan_id=kec.id, name=desa_name, target=0)
        db.add(d_obj)
        db.flush()
        
    # 3. Get/Create UnitSpam (Assuming 1 per village for now)
    unit = db.query(models.UnitSpam).filter(models.UnitSpam.desa_id == d_obj.id).first()
    if not unit:
        unit = models.UnitSpam(
            desa_id=d_obj.id,
            sistem_layanan=sistem_layanan,
            sumber_mata_air_kap=sumber_mata_air_kap,
            sumber_air_tanah_kap=sumber_air_tanah_kap,
            lain_lain_kap=lain_lain_kap,
            sumber_dana=sumber_dana,
            program=program,
            tarif_dasar_hukum=tarif_dasar_hukum,
            iuran_nominal=iuran_nominal,
            biaya_operasional=biaya_operasional
        )
        db.add(unit)
        db.flush()
    else:
        # Update technical data if provided
        if sistem_layanan: unit.sistem_layanan = sistem_layanan
        # ... update other fields as needed
        
    # 4. Get/Create Pengelola
    if not unit.pengelola:
        pengelola = models.Pengelola(
            unit_spam_id=unit.id,
            pokmas=pokmas, perdes=perdes, kepala=kepala,
            bendahara=bendahara, sekretaris=sekretaris
        )
        db.add(pengelola)
    else:
        if pokmas: unit.pengelola.pokmas = pokmas
        if kepala: unit.pengelola.kepala = kepala
        # ...
        
    # 5. Create Achievement (Annual)
    # Check if exists for that year
    existing_ach = db.query(models.Achievement).filter(models.Achievement.unit_spam_id == unit.id, models.Achievement.tahun == tahun).first()
    if existing_ach:
        existing_ach.jumlah_sr = jumlah_sr
        existing_ach.jumlah_kk = jumlah_kk
        existing_ach.jumlah_jiwa = jumlah_kk * 5
        existing_ach.jumlah_bjp_kk = jumlah_bjp_kk
        existing_ach.jumlah_bjp_jiwa = jumlah_bjp_kk * 5
        existing_ach.catatan = catatan
    else:
        new_ach = models.Achievement(
            unit_spam_id=unit.id,
            tahun=tahun,
            jumlah_sr=jumlah_sr,
            jumlah_kk=jumlah_kk,
            jumlah_jiwa=jumlah_kk * 5,
            jumlah_bjp_kk=jumlah_bjp_kk,
            jumlah_bjp_jiwa=jumlah_bjp_kk * 5,
            catatan=catatan
        )
        db.add(new_ach)
        
    db.commit()
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"status": "success", "message": "Berhasil simpan data baru"}
        
    return RedirectResponse(url="/spm", status_code=303)

@app.post("/update/{item_id}")
async def update_item(
    request: Request, 
    item_id: int, # This is the Achievement ID
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
    
    ach = db.query(models.Achievement).filter(models.Achievement.id == item_id).first()
    if ach:
        # Update annual data
        ach.jumlah_sr = jumlah_sr
        ach.jumlah_kk = jumlah_kk
        ach.jumlah_jiwa = jumlah_kk * 5
        ach.jumlah_bjp_kk = jumlah_bjp_kk
        ach.jumlah_bjp_jiwa = jumlah_bjp_kk * 5
        ach.catatan = catatan
        
        # Update UnitSpam data (Technical/Financial)
        unit = ach.unit
        if unit:
            unit.sistem_layanan = sistem_layanan
            unit.sumber_mata_air_kap = sumber_mata_air_kap
            unit.sumber_air_tanah_kap = sumber_air_tanah_kap
            unit.lain_lain_kap = lain_lain_kap
            unit.tarif_dasar_hukum = tarif_dasar_hukum
            unit.iuran_nominal = iuran_nominal
            unit.biaya_operasional = biaya_operasional
            if sumber_dana: unit.sumber_dana = sumber_dana
            if program: unit.program = program
            
            # Update Pengelola
            if unit.pengelola:
                unit.pengelola.pokmas = pokmas
                unit.pengelola.perdes = perdes
                unit.pengelola.kepala = kepala
                unit.pengelola.bendahara = bendahara
                unit.pengelola.sekretaris = sekretaris
            else:
                new_peng = models.Pengelola(
                    unit_spam_id=unit.id,
                    pokmas=pokmas, perdes=perdes, kepala=kepala,
                    bendahara=bendahara, sekretaris=sekretaris
                )
                db.add(new_peng)
                
        db.commit()
        
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"status": "success", "message": "Berhasil update data"}
        
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
    items = data.get("items", []) 
    new_note = data.get("catatan", "")
    target_year = data.get("year", "All")
    
    if not items:
        return {"status": "error", "message": "No data selected"}
        
    for it in items:
        kec_name = it.get("kecamatan")
        desa_name = it.get("desa")
        
        unit = db.query(models.UnitSpam).join(models.Desa).join(models.Kecamatan)\
            .filter(models.Kecamatan.name == kec_name, models.Desa.name == desa_name).first()
            
        if not unit: continue
        
        if target_year != "All":
            db.query(models.Achievement).filter(
                models.Achievement.unit_spam_id == unit.id,
                models.Achievement.tahun == target_year
            ).update({"catatan": new_note}, synchronize_session=False)
        else:
            latest = db.query(models.Achievement).filter(
                models.Achievement.unit_spam_id == unit.id
            ).order_by(models.Achievement.tahun.desc()).first()
            if latest:
                latest.catatan = new_note
                
    db.commit()
    return {"status": "success", "message": f"Berhasil update {len(items)} data."}

@app.get("/api/desa/{kec}")
async def get_villages_by_kec(kec: str, db: Session = Depends(get_db)):
    villages = db.query(models.Desa.name).join(models.Kecamatan)\
        .filter(models.Kecamatan.name == kec).all()
    return sorted([v[0] for v in villages])

@app.post("/api/update-simspam")
async def update_simspam(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request): 
        return {"status": "error", "message": "Unauthorized"}
    data = await request.json()
    kecamatan_name = data.get("kecamatan")
    village_name = data.get("village")
    is_checked = data.get("checked")
    
    unit = db.query(models.UnitSpam).join(models.Desa).join(models.Kecamatan)\
        .filter(models.Kecamatan.name == kecamatan_name, models.Desa.name == village_name).first()
        
    if unit:
        unit.is_simspam = 1 if is_checked else 0
        db.commit()
        
    return {"status": "success"}

@app.get("/api/data")
async def get_all_data(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request): return {"status": "error", "message": "Unauthorized"}
    
    bjp_file_map = load_bjp_data()
    units = db.query(models.UnitSpam).all()
    display_items = []
    for u in units:
        total_sr = sum(a.jumlah_sr or 0 for a in u.achievements)
        total_kk = sum(a.jumlah_kk or 0 for a in u.achievements)
        
        file_bjp = bjp_file_map.get((u.desa.kecamatan.name, u.desa.name), 0)
        total_bjp_kk = file_bjp + sum(a.jumlah_bjp_kk or 0 for a in u.achievements)
        
        years_list = sorted([
            {
                "id": a.id, "tahun": a.tahun,
                "sr": a.jumlah_sr or 0, "kk": a.jumlah_kk or 0, "jiwa": a.jumlah_jiwa or 0,
                "bjp_kk": a.jumlah_bjp_kk or 0, "bjp_jiwa": a.jumlah_bjp_kk * 5,
                "meta": {
                    "sumber_dana": u.sumber_dana, "program": u.program,
                    "catatan": a.catatan
                }
            } for a in u.achievements
        ], key=lambda x: x["tahun"], reverse=True)
        
        display_items.append({
            "unit_id": u.id,
            "kecamatan": u.desa.kecamatan.name,
            "desa": u.desa.name,
            "is_simspam": u.is_simspam,
            "target": u.desa.target,
            "total_sr": total_sr,
            "total_kk": total_kk,
            "bjp_kk": total_bjp_kk,
            "years_list": years_list
        })
        
    display_items = sorted(display_items, key=lambda x: (x["kecamatan"], x["desa"]))
    return {"status": "success", "items": display_items}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
