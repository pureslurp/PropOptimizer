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
        # For Supabase, use connection pooling URL if available
        # Check if it's already a pooling URL
        if 'pooler.supabase.co' in url:
            return url
        
        # Convert direct connection to pooling connection
        if 'db.' in url and 'supabase.co' in url:
            # Replace db. with pooler. for connection pooling
            pooled_url = url.replace('db.', 'pooler.')
            print(f"🔄 Using Supabase connection pooling: {pooled_url[:30]}...")
            return pooled_url
    
    return url

# Optimize URL for Supabase
DATABASE_URL = optimize_database_url_for_supabase(DATABASE_URL)

# Create engine with connection pooling for Supabase
# Add connection pooling settings for better cloud performance
engine = create_engine(
    DATABASE_URL, 
    echo=False,  # Set to True for SQL debugging
    pool_size=5,  # Number of connections to maintain in pool
    max_overflow=10,  # Additional connections that can be created
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,  # Recycle connections after 5 minutes
    connect_args={
        "connect_timeout": 10,  # Connection timeout in seconds
        "application_name": "prop_optimizer"  # Identify this app in Supabase logs
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Create metadata
metadata = MetaData()
