from supabase import create_client
from django.conf import settings

supabase_storage = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)