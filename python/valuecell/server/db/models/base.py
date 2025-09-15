"""Base model for ValueCell Server."""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase

# Create the base class for all models
Base = declarative_base()

# Alternative approach using modern SQLAlchemy 2.0 style
# class Base(DeclarativeBase):
#     pass