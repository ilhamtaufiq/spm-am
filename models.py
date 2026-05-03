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

class Kecamatan(Base):
    __tablename__ = "kecamatan"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    
    desa = relationship("Desa", back_populates="kecamatan")

class Desa(Base):
    __tablename__ = "desa"
    id = Column(Integer, primary_key=True)
    kecamatan_id = Column(Integer, ForeignKey("kecamatan.id"))
    name = Column(String, index=True)
    target = Column(Integer, default=0)
    
    kecamatan = relationship("Kecamatan", back_populates="desa")
    units = relationship("UnitSpam", back_populates="desa")
    
    __table_args__ = (UniqueConstraint('kecamatan_id', 'name', name='_kec_desa_uc'),)

class UnitSpam(Base):
    __tablename__ = "unit_spam"
    id = Column(Integer, primary_key=True)
    desa_id = Column(Integer, ForeignKey("desa.id"))
    name = Column(String, nullable=True)
    is_simspam = Column(Integer, default=0)
    
    # Data Teknis
    sistem_layanan = Column(String)
    sumber_mata_air_kap = Column(String)
    sumber_air_tanah_kap = Column(String)
    lain_lain_kap = Column(String)
    sumber_dana = Column(String)
    program = Column(String)
    
    # Keuangan
    tarif_dasar_hukum = Column(String)
    iuran_nominal = Column(String)
    biaya_operasional = Column(String)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    desa = relationship("Desa", back_populates="units")
    pengelola = relationship("Pengelola", back_populates="unit", uselist=False)
    achievements = relationship("Achievement", back_populates="unit")
    checklists = relationship("UnitChecklist", back_populates="unit")

class Pengelola(Base):
    __tablename__ = "pengelola"
    id = Column(Integer, primary_key=True)
    unit_spam_id = Column(Integer, ForeignKey("unit_spam.id"), unique=True)
    pokmas = Column(String)
    perdes = Column(String)
    kepala = Column(String)
    bendahara = Column(String)
    sekretaris = Column(String)
    
    unit = relationship("UnitSpam", back_populates="pengelola")

class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True)
    unit_spam_id = Column(Integer, ForeignKey("unit_spam.id"))
    tahun = Column(String, index=True)
    jumlah_sr = Column(Integer, default=0)
    jumlah_kk = Column(Integer, default=0)
    jumlah_jiwa = Column(Integer, default=0)
    jumlah_bjp_kk = Column(Integer, default=0)
    jumlah_bjp_jiwa = Column(Integer, default=0)
    catatan = Column(String)
    
    unit = relationship("UnitSpam", back_populates="achievements")
    __table_args__ = (UniqueConstraint('unit_spam_id', 'tahun', name='_unit_tahun_uc'),)

class UnitChecklist(Base):
    __tablename__ = "unit_checklists"
    id = Column(Integer, primary_key=True)
    unit_spam_id = Column(Integer, ForeignKey("unit_spam.id"))
    item = Column(String)
    is_checked = Column(Integer, default=0)
    
    unit = relationship("UnitSpam", back_populates="checklists")

class AchievementLegacy(Base):
    __tablename__ = "achievements_legacy"

    id = Column(Integer, primary_key=True, index=True)
    no_urut = Column(Integer)
    kecamatan = Column(String, index=True)
    desa = Column(String, index=True)
    tahun = Column(String, index=True)
    sumber_dana = Column(String)
    program = Column(String)
    pokmas = Column(String)
    perdes = Column(String)
    kepala = Column(String)
    bendahara = Column(String)
    sekretaris = Column(String)
    sumber_mata_air_kap = Column(String)
    sistem_layanan = Column(String)
    sumber_air_tanah_kap = Column(String)
    lain_lain_kap = Column(String)
    tarif_dasar_hukum = Column(String)
    iuran_nominal = Column(String)
    pendapatan_rata2 = Column(String)
    biaya_operasional = Column(String)
    jumlah_sr = Column(Integer, default=0)
    jumlah_kk = Column(Integer, default=0)
    jumlah_jiwa = Column(Integer, default=0)
    jumlah_bjp_kk = Column(Integer, default=0)
    jumlah_bjp_jiwa = Column(Integer, default=0)
    target = Column(Integer, default=0)
    catatan = Column(String)
    is_simspam = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

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

