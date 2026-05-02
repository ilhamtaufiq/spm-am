from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/spm_am.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    no_urut = Column(Integer)
    kecamatan = Column(String)
    desa = Column(String)
    tahun = Column(String)
    sumber_dana = Column(String)
    program = Column(String)
    pokmas = Column(String)
    
    # Pengurus / Kelembagaan
    perdes = Column(String)
    kepala = Column(String)
    bendahara = Column(String)
    sekretaris = Column(String)
    
    # Data Teknis
    sumber_mata_air_kap = Column(String)
    sistem_layanan = Column(String) # Gravitasi/Pompa
    sumber_air_tanah_kap = Column(String)
    lain_lain_kap = Column(String)
    
    # Parameter
    tarif_dasar_hukum = Column(String)
    iuran_nominal = Column(String)
    pendapatan_rata2 = Column(String)
    biaya_operasional = Column(String)
    
    # Numeric values (Rounded)
    jumlah_sr = Column(Integer, default=0)
    jumlah_kk = Column(Integer, default=0)
    jumlah_jiwa = Column(Integer, default=0)
    jumlah_bjp_kk = Column(Integer, default=0)
    jumlah_bjp_jiwa = Column(Integer, default=0)
    target = Column(Integer, default=0)
    catatan = Column(String)

class RemiGame(Base):
    __tablename__ = "remi_games"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(String)
    is_active = Column(Integer, default=1)
    winner_name = Column(String, nullable=True)

class RemiPlayer(Base):
    __tablename__ = "remi_players"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer)
    name = Column(String)
    total_score = Column(Integer, default=0)

class RemiRound(Base):
    __tablename__ = "remi_rounds"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer)
    player_id = Column(Integer)
    points = Column(Integer)
    round_number = Column(Integer)

