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
        # For Supabase, try connection pooling URL first, then fall back to direct
        if 'db.' in url and 'supabase.co' in url:
            # Extract credentials and region from the URL
            # Format: postgresql://user:pass@db.project.supabase.co:5432/postgres
            try:
                import re
                match = re.match(r'postgresql://([^:]+):([^@]+)@db\.([^.]+)\.supabase\.co:(\d+)/(.+)', url)
                if match:
                    user, password, project_id, port, database = match.groups()
                    
                    # Try connection pooling URL format
                    # This is Supabase's recommended format for serverless/cloud apps
                    pooled_url = f"postgresql://{user}:{password}@aws-0-us-east-1.pooler.supabase.com:6543/{database}"
                    print(f"🔄 Trying Supabase connection pooling: {pooled_url[:30]}...")
                    return pooled_url
            except Exception as e:
                print(f"⚠️ Could not parse URL for pooling: {e}")
        
        # Fall back to direct connection
        print(f"🔄 Using Supabase direct connection: {url[:30]}...")
        return url
    
    return url

# Optimize URL for Supabase
DATABASE_URL = optimize_database_url_for_supabase(DATABASE_URL)

# Create engine with connection pooling for Supabase
# Add connection pooling settings optimized for Streamlit Cloud
engine = create_engine(
    DATABASE_URL, 
    echo=True,  # Enable SQL debugging to see connection attempts
    pool_size=1,  # Minimal pool size for cloud deployment
    max_overflow=0,  # No overflow connections to avoid issues
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=120,  # Recycle connections after 2 minutes
    pool_timeout=60,  # Wait up to 60 seconds for a connection
    connect_args={
        "connect_timeout": 60,  # Longer connection timeout for cloud
        "application_name": "prop_optimizer_streamlit",  # Identify this app in Supabase logs
        "options": "-c default_transaction_isolation=read_committed"
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Create metadata
metadata = MetaData()
