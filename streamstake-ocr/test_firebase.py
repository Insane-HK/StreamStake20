
import firebase_admin
from firebase_admin import credentials, db
import os
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Load env
load_dotenv()

def test_firebase_connection():
    print("="*50)
    print("FIREBASE CONNECTION TEST")
    print("="*50)

    # 1. Check Env Vars
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
    private_key = os.getenv("FIREBASE_PRIVATE_KEY")
    db_url = os.getenv("FIREBASE_DATABASE_URL")

    print(f"Project ID: {project_id}")
    print(f"Client Email: {client_email}")
    print(f"Database URL: {db_url}")
    print(f"Private Key: {'[SET]' if private_key else '[MISSING]'}")

    if not all([project_id, client_email, private_key, db_url]):
        print("\n❌ MISSING ENVIRONMENT VARIABLES")
        print("Please check your .env file and ensure all 4 variables are set.")
        return

    # 2. Try to Init App
    try:
        if not firebase_admin._apps:
            cred_dict = {
                "type": "service_account",
                "project_id": project_id,
                "private_key": private_key.replace('\\n', '\n'),
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': db_url
            })
            print("\n✅ Firebase App Initialized")
        else:
             print("\nℹ️ Firebase App already initialized")

    except Exception as e:
        print(f"\n❌ FAILED TO INITIALIZE APP: {e}")
        print("Tip: Check if your Private Key is copied correctly (including -----BEGIN...).")
        return

    # 3. Try to Write to DB
    try:
        ref = db.reference('/test_connection')
        ref.set({
            "status": "connected", 
            "message": "Hello from StreamStake OCR",
            "timestamp": {".sv": "timestamp"}
        })
        print("✅ Write Test Successful (wrote to /test_connection)")
        
        # 4. Try to Read
        data = ref.get()
        print(f"✅ Read Test Successful: {data}")
        
    except Exception as e:
        print(f"\n❌ DATABASE OPERATION FAILED: {e}")
        print("Tip: Check your Database Rules and Database URL.")

if __name__ == "__main__":
    test_firebase_connection()
