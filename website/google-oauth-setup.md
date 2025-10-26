# Google OAuth Setup Instructions

## Overview
The Google authentication has been implemented in both login.html and register.html. To make it fully functional, you need to set up a Google OAuth client ID.

## Steps to Complete Setup

### 1. Create a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API or Google Identity API

### 2. Configure OAuth Consent Screen
1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type (unless you have a Google Workspace account)
3. Fill in the required information:
   - App name: "TOPCIT Quest"
   - User support email: Your email
   - Developer contact information: Your email

### 3. Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Web application" as the application type
4. Add authorized JavaScript origins:
   - `http://localhost:8000` (for local development)
   - Your production domain (when deployed)
5. Add authorized redirect URIs (if needed):
   - `http://localhost:8000` (for local development)
   - Your production domain (when deployed)

### 4. Update the Code
1. Copy the Client ID from the Google Cloud Console
2. Replace `YOUR_GOOGLE_CLIENT_ID` in both login.html and register.html with your actual Client ID

### 5. Test the Implementation
1. Start your local server: `python -m http.server 8000`
2. Navigate to the login or register page
3. Click the "Sign up with Google" or "Continue with Google" button
4. Complete the Google authentication flow

## Current Implementation Features
- ✅ Google Identity Services library loaded
- ✅ OAuth initialization on page load
- ✅ JWT token parsing to extract user information
- ✅ User profile picture integration
- ✅ Error handling for authentication failures
- ✅ Consistent user data storage format
- ✅ Profile modal integration with Google data

## Security Notes
- The Client ID is safe to expose in client-side code
- User authentication is handled securely by Google
- JWT tokens are parsed client-side to extract user information
- No sensitive credentials are stored in the code

## Troubleshooting
- Ensure your domain is added to authorized origins
- Check browser console for any JavaScript errors
- Verify the Client ID is correctly set
- Make sure the Google Identity Services library loads properly