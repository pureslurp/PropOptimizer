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

def optimize_database_url_for_supabase(url):
    """Optimize database URL for Supabase cloud deployment"""
    if 'supabase.co' in url:
        # For Supabase, ensure we're using the direct connection URL
        # Connection pooling is handled by SQLAlchemy's pool settings
        print(f"🔄 Using Supabase direct connection: {url[:30]}...")
        return url
    
    return url

# Optimize URL for Supabase
DATABASE_URL = optimize_database_url_for_supabase(DATABASE_URL)

# Create engine with connection pooling for Supabase
# Add connection pooling settings optimized for Streamlit Cloud
engine = create_engine(
    DATABASE_URL, 
    echo=False,  # Set to True for SQL debugging
    pool_size=1,  # Minimal pool size for cloud deployment
    max_overflow=2,  # Few additional connections
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=180,  # Recycle connections after 3 minutes
    pool_timeout=30,  # Wait up to 30 seconds for a connection
    connect_args={
        "connect_timeout": 30,  # Longer connection timeout for cloud
        "application_name": "prop_optimizer",  # Identify this app in Supabase logs
        "options": "-c default_transaction_isolation=read_committed"
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Create metadata
metadata = MetaData()
