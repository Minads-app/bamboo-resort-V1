"""
Helper script to convert firebase_key.json to Streamlit secrets format
Run this script to generate the secrets content for Streamlit Cloud
"""
import json
import os

def convert_firebase_key_to_secrets():
    """Read firebase_key.json and output secrets.toml format"""
    try:
        # Check config dir first
        config_path = 'config/firebase_key.json'
        # Fallback to root (legacy) if not found in config, but warn?
        # Actually just check config first as per plan.
        if not os.path.exists(config_path) and os.path.exists('firebase_key.json'):
             config_path = 'firebase_key.json'
             
        with open(config_path, 'r', encoding='utf-8') as f:
            firebase_data = json.load(f)
        
        print("=" * 60)
        print("COPY THE CONTENT BELOW TO STREAMLIT CLOUD SECRETS")
        print("=" * 60)
        print()
        print("[firebase]")
        print(f'type = "{firebase_data.get("type", "")}"')
        print(f'project_id = "{firebase_data.get("project_id", "")}"')
        print(f'private_key_id = "{firebase_data.get("private_key_id", "")}"')
        
        # Private key needs special handling - preserve newlines
        private_key = firebase_data.get("private_key", "").replace("\n", "\\n")
        print(f'private_key = "{private_key}"')
        
        print(f'client_email = "{firebase_data.get("client_email", "")}"')
        print(f'client_id = "{firebase_data.get("client_id", "")}"')
        print(f'auth_uri = "{firebase_data.get("auth_uri", "")}"')
        print(f'token_uri = "{firebase_data.get("token_uri", "")}"')
        print(f'auth_provider_x509_cert_url = "{firebase_data.get("auth_provider_x509_cert_url", "")}"')
        print(f'client_x509_cert_url = "{firebase_data.get("client_x509_cert_url", "")}"')
        print()
        print("=" * 60)
        print("✅ Copy everything above and paste into Streamlit Cloud")
        print("   Advanced Settings > Secrets")
        print("=" * 60)
        
    except FileNotFoundError:
        print("❌ Error: firebase_key.json not found!")
        print("   Make sure you run this script in the project root directory.")
    except json.JSONDecodeError:
        print("❌ Error: firebase_key.json is not valid JSON!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    convert_firebase_key_to_secrets()
