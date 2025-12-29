from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer, nullable=False) # Guardamos como entero (CLP suele ser sin decimales), o Float si prefiere.
    concept = Column(String, nullable=False)
    category = Column(String, nullable=False, default="General")
    date = Column(Date, default=date.today)
    image_url = Column(String, nullable=True) # Link a la boleta (futuro)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="expenses")
