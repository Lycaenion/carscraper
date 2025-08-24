import sqlite3
import sqlalchemy
from datetime import date
from sqlalchemy import (
    create_engine, String, Integer, ForeignKey, select, delete
)
from sqlalchemy.orm import (
    sessionmaker, DeclarativeBase, relationship, mapped_column, Mapped, MappedAsDataclass, Session
)
from typing import List, Optional

SQLALCHEMY_DATABASE_URI = 'sqlite:///project_db.sqlite'

class Base(MappedAsDataclass, DeclarativeBase):
    """Base class for declarative models with dataclass support"""

engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=True, echo_pool='debug')
Session = sessionmaker(bind=engine)

class Webpage(Base):
    __tablename__ = "webpages"
    __table_args__ = {'sqlite_autoincrement' : True}

    id: Mapped[int] = mapped_column(init=False, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(30), nullable=False)
    page_name: Mapped[str] = mapped_column(String(50), nullable=False)
    advertisements: Mapped[Optional[List["Advertisement"]]] = relationship(
        back_populates="webpage",
        default_factory=list
    )

class Advertisement(Base):
    __tablename__ = "advertisements"
    __table_args__ = {'sqlite_autoincrement' : True}

    id: Mapped[int] = mapped_column(init=False, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    webpage_id: Mapped[int] = mapped_column(ForeignKey('webpages.id'), nullable=False)
    webpage: Mapped[Webpage] = relationship(back_populates='advertisements')
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=True)
    year: Mapped[str] = mapped_column(String(20), nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=True)
    mileage: Mapped[str] = mapped_column(String(100), nullable=True)
    gearbox: Mapped[str] = mapped_column(String(100), nullable=True)
    fuel_type: Mapped[str] = mapped_column(String(100), nullable=True)
    engine_power: Mapped[str] = mapped_column(String(100), nullable=True)
    location: Mapped[str] = mapped_column(String(100), nullable=True)
    date_added: Mapped[str] = mapped_column(String(100), default=None, nullable=False, comment='date added to db')

# Create tables
Base.metadata.create_all(bind=engine)

def add_to_db(url: str,
              webpage_name: str,
              brand: str,
              model_version: str,
              year: str,
              price: int,
              mileage: str,
              gearbox: str,
              fuel_type: str,
              engine_power: str,
              location: str) -> None:
    try:
        with Session() as session:
            with session.begin():
                date_added = date.today().isoformat()
                webpage = session.query(Webpage).filter_by(page_name = webpage_name).first()
                if not webpage:
                    print(f'webpage not found: {webpage_name}')
                    return
                advertisement = Advertisement(
                    url=url,
                    webpage_id=webpage.id,
                    webpage=webpage,
                    brand=brand,
                    model_version=model_version,
                    year=year,
                    price=price,
                    mileage=mileage,
                    gearbox=gearbox,
                    fuel_type=fuel_type,
                    engine_power=engine_power,
                    location=location,
                    date_added=date_added
                )
                session.add(advertisement)
                print(f'advertisement added: {advertisement}')

    except sqlalchemy.exc.IntegrityError:
        print("Duplicate entry or constraint violation. Skipping this advertisement.")
    except Exception as e:
        print(f"Error adding to database: {e}")

def if_advertisement_exists(url: str) -> bool:
    try:
        with Session() as session:
            exists = session.query(Advertisement).filter_by(url = url).first()
            return exists
    except Exception as e:
        print(f"Error checking advertisement existence: {e}")
        return False



if __name__ == '__main__':
    webpage1 = Webpage(url='https://www.autoscout24.com', page_name='autoscout24')
    webpage2 = Webpage(url='https://www.autovia.sk', page_name='autovia')

    with Session() as session:
        session.add(webpage1)
        session.add(webpage2)
        session.commit()