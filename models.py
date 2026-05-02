from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
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
    kecamatan = Column(String, index=True)
    desa = Column(String, index=True)
    tahun = Column(String, index=True)
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

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (UniqueConstraint('kecamatan', 'desa', 'tahun', name='_desa_tahun_uc'),)

class RemiGame(Base):
    __tablename__ = "remi_games"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Integer, default=1)
    winner_name = Column(String, nullable=True)
    
    players = relationship("RemiPlayer", back_populates="game", cascade="all, delete-orphan")
    rounds = relationship("RemiRound", back_populates="game", cascade="all, delete-orphan")

class RemiPlayer(Base):
    __tablename__ = "remi_players"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("remi_games.id"))
    name = Column(String)
    total_score = Column(Integer, default=0)
    
    game = relationship("RemiGame", back_populates="players")
    rounds = relationship("RemiRound", back_populates="player", cascade="all, delete-orphan")

class RemiRound(Base):
    __tablename__ = "remi_rounds"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("remi_games.id"))
    player_id = Column(Integer, ForeignKey("remi_players.id"))
    points = Column(Integer)
    round_number = Column(Integer)

    game = relationship("RemiGame", back_populates="rounds")
    player = relationship("RemiPlayer", back_populates="rounds")

