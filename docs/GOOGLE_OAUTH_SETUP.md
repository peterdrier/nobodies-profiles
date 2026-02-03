# Google OAuth Setup

This document explains how to set up Google OAuth for the Nobodies Profiles application.

## Prerequisites

- A Google account
- Access to Google Cloud Console

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it something like "Nobodies Profiles"
4. Click "Create"

## Step 2: Enable Required APIs

1. In your project, go to "APIs & Services" → "Library"
2. Search for and enable:
   - "Google+ API" (for basic profile info)
   - Or "People API" (newer alternative)

## Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type (unless you have Google Workspace)
3. Fill in the required fields:
   - **App name**: Nobodies Profiles
   - **User support email**: your email
   - **Developer contact**: your email
4. Click "Save and Continue"
5. For Scopes, add:
   - `email`
   - `profile`
   - `openid`
6. Click "Save and Continue"
7. Add test users if in testing mode

## Step 4: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: **Web application**
4. Name: "Nobodies Profiles Web"
5. Add Authorized JavaScript origins:
   - `http://localhost:8000` (development)
   - `https://profiles.nobodies.team` (production, when ready)
6. Add Authorized redirect URIs:
   - `http://localhost:8000/accounts/google/login/callback/`
   - `https://profiles.nobodies.team/accounts/google/login/callback/`
7. Click "Create"
8. Copy the **Client ID** and **Client Secret**

## Step 5: Configure the Application

### Option A: Environment Variables (Recommended)

Add to your `.env` file:

```bash
GOOGLE_OAUTH_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret-here
```

### Option B: Django Admin (Alternative)

1. Start the development server
2. Go to `/admin/`
3. Navigate to "Social Applications"
4. Add a new application:
   - Provider: Google
   - Name: Google
   - Client ID: your client ID
   - Secret key: your client secret
   - Sites: add your site (localhost:8000 or production domain)

## Step 6: Configure Site in Django Admin

1. Go to `/admin/sites/site/`
2. Change the default site (ID: 1) to:
   - Domain: `localhost:8000` (or your production domain)
   - Display name: "Nobodies Profiles"

## Step 7: Test the Setup

1. Start the development server: `python manage.py runserver`
2. Visit `http://localhost:8000/`
3. Click "Sign in with Google"
4. Complete the Google OAuth flow
5. You should be redirected back and logged in

## Troubleshooting

### "Error 400: redirect_uri_mismatch"

The redirect URI in Google Cloud Console doesn't match. Make sure you have:
- `http://localhost:8000/accounts/google/login/callback/`

Note the trailing slash!

### "Access blocked: This app's request is invalid"

Your OAuth consent screen may not be configured correctly, or you need to add yourself as a test user.

### "Social Network Login Failure"

Check that:
1. The Site model is configured correctly
2. The SocialApp is linked to the correct Site
3. Your Client ID and Secret are correct

## Production Considerations

1. Move OAuth consent screen to "Production" status
2. Update redirect URIs for production domain
3. Consider using Google Workspace domain restriction if applicable
