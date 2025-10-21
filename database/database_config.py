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
        # For Supabase, use transaction mode pooling for serverless apps like Streamlit Cloud
        # Format: postgres://postgres.[PROJECT_ID]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
        if 'db.' in url and 'supabase.co' in url:
            try:
                import re
                # Parse the direct connection URL
                # Format: postgresql://user:pass@db.project.supabase.co:5432/postgres
                match = re.match(r'postgresql://([^:]+):([^@]+)@db\.([^.]+)\.supabase\.co:(\d+)/(.+)', url)
                if match:
                    user, password, project_id, port, database = match.groups()
                    
                    # Convert to Supavisor transaction mode URL for serverless apps
                    # This is the recommended format for Streamlit Cloud
                    pooled_url = f"postgresql://postgres.{project_id}:{password}@aws-0-us-east-1.pooler.supabase.com:6543/{database}"
                    print(f"🔄 Using Supavisor transaction mode for serverless: {pooled_url[:40]}...")
                    return pooled_url
            except Exception as e:
                print(f"⚠️ Could not parse URL for pooling: {e}")
                print(f"🔄 Falling back to direct connection: {url[:30]}...")
                return url
        
        # Fall back to direct connection if parsing fails
        print(f"🔄 Using Supabase direct connection: {url[:30]}...")
        return url
    
    return url

# Optimize URL for Supabase
DATABASE_URL = optimize_database_url_for_supabase(DATABASE_URL)

# Create engine with connection pooling for Supabase
# Add connection pooling settings optimized for Supavisor transaction mode
engine = create_engine(
    DATABASE_URL, 
    echo=True,  # Enable SQL debugging to see connection attempts
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
