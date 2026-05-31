import firebase_admin
from firebase_admin import credentials, auth
import os

# Firebase Service Account Key
firebase_private_key = os.getenv("FIREBASE_PRIVATE_KEY")
if firebase_private_key:
    firebase_private_key = firebase_private_key.replace('\\n', '\n')

firebase_creds = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": firebase_private_key,
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN")
}

if not firebase_admin._apps:
    if firebase_creds.get("project_id") and firebase_creds.get("private_key"):
        try:
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Warning: Firebase Admin failed to initialize: {e}")
    else:
        print("Warning: Firebase credentials are not fully configured in the environment. Firebase authentication will fallback.")

def verify_firebase_token(id_token):
    try:
        # clock_skew_seconds=5 tolerates minor clock drift between client and Google servers
        decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=5)
        return decoded_token
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None

def create_custom_token(uid):
    try:
        custom_token = auth.create_custom_token(uid)
        return custom_token.decode('utf-8')
    except Exception as e:
        print(f"Error creating custom token: {e}")
        return None
def delete_firebase_user(uid):
    try:
        auth.delete_user(uid)
        return True
    except Exception as e:
        print(f"Error deleting Firebase user: {e}")
        return False
