from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_KEY

# Create Supabase client
# This replaces the MongoDB motor client
# All routes use this supabase object to query the database
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)