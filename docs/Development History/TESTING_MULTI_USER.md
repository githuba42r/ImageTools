# Testing Multi-User Sessions

This document explains how to test multiple user sessions in development mode using the `VITE_SESSION_OVERRIDE` environment variable.

## Overview

The session override feature allows you to simulate different users by setting a custom session ID. This is useful for:
- Testing Basic Auth integration
- Testing Authelia cookie-based authentication
- Simulating multiple users without actual authentication
- Development and debugging of multi-user scenarios

## How It Works

When `VITE_SESSION_OVERRIDE` is set in the frontend `.env` file:
1. The session store will use the override value as the session ID
2. LocalStorage is bypassed (to avoid conflicts between test sessions)
3. If the session doesn't exist on the backend, it will be created with that ID
4. If the session exists, it will be reused and expiry extended

## Setup Instructions

### 1. Edit Frontend Environment File

Open `/home/philg/working/ImageTools/frontend/.env` and set the session override:

```bash
# For User 1
VITE_SESSION_OVERRIDE=user1

# For User 2
VITE_SESSION_OVERRIDE=user2

# For User 3
VITE_SESSION_OVERRIDE=user3
```

### 2. Test Multiple Users

#### Option A: Multiple Browser Profiles

1. Create different browser profiles (Chrome, Firefox, etc.)
2. Set different `VITE_SESSION_OVERRIDE` values for each
3. Run `npm run dev` in each terminal with different override values
4. Each browser profile will connect to its respective session

#### Option B: Multiple Terminal Windows

**Terminal 1 (User 1):**
```bash
cd frontend
# Edit .env to set VITE_SESSION_OVERRIDE=user1
npm run dev -- --port 5173
```

**Terminal 2 (User 2):**
```bash
cd frontend
# Edit .env to set VITE_SESSION_OVERRIDE=user2
npm run dev -- --port 5174
```

**Terminal 3 (User 3):**
```bash
cd frontend
# Edit .env to set VITE_SESSION_OVERRIDE=user3
npm run dev -- --port 5175
```

#### Option C: Use .env.local for Override

Create different `.env.local` files that override the main `.env`:

```bash
# .env.local.user1
VITE_API_URL=http://localhost:8081
VITE_SESSION_OVERRIDE=user1

# .env.local.user2
VITE_API_URL=http://localhost:8081
VITE_SESSION_OVERRIDE=user2
```

Then run with:
```bash
cp .env.local.user1 .env.local && npm run dev -- --port 5173
cp .env.local.user2 .env.local && npm run dev -- --port 5174
```

## Verification

To verify that sessions are isolated:

1. Open User 1's instance and upload an image
2. Open User 2's instance and verify the image is NOT visible
3. Check browser console for log: `Using session override: user1`
4. Check backend logs for session creation/validation

## Backend Verification

You can check the sessions in the database:

```bash
cd backend
sqlite3 storage/imagetools.db "SELECT id, user_id, created_at, expires_at FROM sessions;"
```

You should see entries like:
```
user1|NULL|2025-02-07 10:00:00|2025-02-14 10:00:00
user2|NULL|2025-02-07 10:05:00|2025-02-14 10:05:00
user3|NULL|2025-02-07 10:10:00|2025-02-14 10:10:00
```

## Integration with Authentication

When integrating with Basic Auth or Authelia:

1. The authentication system sets a cookie (e.g., `Remote-User`)
2. Your backend middleware can extract the username from the cookie
3. Use that username as the `custom_session_id` when creating sessions
4. Frontend can read the cookie and pass it to the session API

Example flow:
```
1. User logs in via Authelia → Cookie: Remote-User=john
2. Frontend reads cookie → Creates session with ID "john"
3. Backend creates/retrieves session with ID "john"
4. All operations use session ID "john"
```

## Disabling Override

To return to normal operation (auto-generated session IDs):

```bash
# In .env, set to empty or remove the line
VITE_SESSION_OVERRIDE=
```

Or comment it out:
```bash
# VITE_SESSION_OVERRIDE=user1
```

## Important Notes

- ⚠️ **This is for development/testing only**
- ⚠️ Do not use simple session IDs in production (use UUIDs or secure tokens)
- ⚠️ Session override bypasses localStorage to avoid conflicts
- ⚠️ Each session is isolated - images, history, and settings are per-session
- ⚠️ Sessions expire after 7 days (configurable in backend config)

## Troubleshooting

**Issue**: Changes not taking effect
- **Solution**: Restart the dev server after changing `.env`

**Issue**: Sessions mixing between users
- **Solution**: Verify `VITE_SESSION_OVERRIDE` is set correctly and dev server restarted

**Issue**: Can't see different user's images
- **Solution**: This is expected behavior - sessions are isolated

**Issue**: Session validation failing
- **Solution**: Check backend logs and ensure the backend is running
