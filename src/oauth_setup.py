import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If you modify these scopes, delete token.json so you can re-do the flow.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def main():
    creds = None
    # 1) Look for existing token.json
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # 2) If no valid credentials, run the OAuth flow:
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # 3) Save the credentials for next time
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())
    print("OAuth setup complete. token.json created.")

if __name__ == "__main__":
    main()
