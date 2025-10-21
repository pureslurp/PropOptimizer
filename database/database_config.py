import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import streamlit as st

# Database configuration
# Get connection string from environment variable or Streamlit secrets
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    # Try to get from Streamlit secrets
    try:
        if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
            DATABASE_URL = st.secrets['DATABASE_URL']
    except:
        pass

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required. Please set it in your Streamlit Cloud app settings under Environment Variables.")

# Create engine
engine = create_engine(DATABASE_URL, echo=False)  # Set to True for SQL debugging

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Create metadata
metadata = MetaData()
