# 🚀 Deployment Guide - Render

Step-by-step guide to deploy Tennis Elbow Hub on Render.

---

## Prerequisites

1. **GitHub account** - Push your code to GitHub
2. **Render account** - Sign up at [render.com](https://render.com) (free)
3. **Domain (optional)** - From Namecheap or any registrar

---

## Step 1: Push to GitHub

```bash
# Initialize git if not already done
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Tennis Elbow Hub"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/tennis-elbow-hub.git
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy on Render

### Option A: Blueprint (Automatic)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New"** → **"Blueprint"**
3. Connect your GitHub repo
4. Render detects `render.yaml` and creates both services

### Option B: Manual Setup

#### Deploy Backend First:

1. Click **"New"** → **"Web Service"**
2. Connect your GitHub repo
3. Configure:
   - **Name**: `tennis-elbow-hub-api`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables:
   - `APP_ENV` = `production`
   - `DEBUG` = `false`
   - `LIVE_SCORES_URL` = `your-private-url`
5. Click **"Create Web Service"**
6. **Copy the URL** (e.g., `https://tennis-elbow-hub-api.onrender.com`)

#### Deploy Frontend:

1. Click **"New"** → **"Static Site"**
2. Connect same GitHub repo
3. Configure:
   - **Name**: `tennis-elbow-hub-web`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. Add Environment Variables:
   - `VITE_API_URL` = `https://tennis-tracker-api.onrender.com` (your backend URL)
5. Click **"Create Static Site"**

---

## Step 3: Configure CORS

After both are deployed, update the backend's `CORS_ORIGINS`:

1. Go to your API service on Render
2. Click **"Environment"**
3. Add/update `CORS_ORIGINS` with your frontend URL:
   ```
   https://tennis-tracker-web.onrender.com
   ```
4. Click **"Save Changes"** (triggers redeploy)

---

## Step 4: Custom Domain (Optional)

### On Render:

1. Go to your Static Site → **"Settings"** → **"Custom Domains"**
2. Add your domain (e.g., `tennistrack.com`)
3. Copy the CNAME record shown

### On Namecheap:

1. Go to **Domain List** → **Manage** → **Advanced DNS**
2. Add a **CNAME Record**:
   - Host: `@` or `www`
   - Value: The CNAME from Render
   - TTL: Automatic
3. Wait 5-30 minutes for DNS propagation

### For API subdomain:

1. Add `api.tennistrack.com` to your API service
2. Create another CNAME record pointing to the API service

---

## Step 5: Verify Deployment

1. Visit your frontend URL
2. Check the Live Scores page loads
3. Upload a match log to test analysis
4. Verify API docs at `https://your-api-url/docs`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS error | Check `CORS_ORIGINS` includes frontend URL with `https://` |
| API 404 | Verify backend deployed and health check passes |
| WebSocket fails | Render supports WebSockets, check for firewall issues |
| Build fails | Check Render logs for specific error |

---

## Environment Variables Summary

### Backend:
| Variable | Value |
|----------|-------|
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `CORS_ORIGINS` | Your frontend URL |
| `LIVE_SCORES_URL` | Your private scores URL |

### Frontend:
| Variable | Value |
|----------|-------|
| `VITE_API_URL` | Your backend URL |

---

## Costs

| Service | Free Tier | Paid |
|---------|-----------|------|
| Web Service | 750 hrs/mo, sleeps after 15min idle | $7/mo (always on) |
| Static Site | Unlimited | - |

> 💡 Free tier is fine for testing. Upgrade when you need always-on service.
