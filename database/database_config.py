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
    """Use the provided DATABASE_URL as-is for Supabase deployment, removing invalid parameters"""
    # Remove pgbouncer=true parameter as it's not valid for SQLAlchemy
    if '?pgbouncer=true' in url:
        url = url.replace('?pgbouncer=true', '')
    return url

# Optimize URL for Supabase
DATABASE_URL = optimize_database_url_for_supabase(DATABASE_URL)

# Create engine with connection pooling for Supabase
# Add connection pooling settings optimized for Supavisor transaction mode
engine = create_engine(
    DATABASE_URL, 
    echo=False,  # Disable SQL debugging for production
    pool_size=1,  # Minimal pool size for serverless deployment
    max_overflow=0,  # No overflow connections
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,  # Recycle connections after 5 minutes
    pool_timeout=30,  # Wait up to 30 seconds for a connection
    connect_args={
        "connect_timeout": 30,  # Connection timeout for cloud
        "application_name": "prop_optimizer_streamlit",  # Identify this app in Supabase logs
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Create metadata
metadata = MetaData()
