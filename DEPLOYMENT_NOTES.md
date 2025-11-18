# Deployment Guide for HDFC MF Chatbot

## ⚠️ Important: Vercel Limitations

**This RAG system is NOT suitable for Vercel deployment** due to:

### Technical Limitations:
1. **Size Limits**:
   - Vercel: 250MB max deployment size
   - Our app: FAISS index + embeddings + models = ~500MB+

2. **Memory Limits**:
   - Vercel Hobby: 1GB RAM
   - Vercel Pro: 3GB RAM
   - Our app needs: 4-6GB for sentence transformers + FAISS

3. **Cold Starts**:
   - Serverless functions restart frequently
   - Models must reload on each cold start (5-10 seconds)
   - Poor user experience

4. **Execution Timeout**:
   - Vercel Hobby: 10 seconds max
   - Vercel Pro: 30 seconds max
   - RAG retrieval + LLM generation can take 15-30 seconds

---

## ✅ Recommended Deployment Options

### Option 1: Split Deployment (Recommended for Demo)

**Frontend**: Vercel (free, fast)  
**Backend**: Railway, Render, or fly.io (better for Python + ML)

#### Steps:

**1. Deploy Backend to Railway** (Recommended - Free $5 credit):
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create new project
railway init

# Deploy backend
railway up

# Note the backend URL (e.g., https://your-app.railway.app)
```

**2. Deploy Frontend to Vercel**:
```bash
cd web

# Update API URL in .env.production
echo "NEXT_PUBLIC_API_URL=https://your-app.railway.app" > .env.production

# Deploy to Vercel
vercel --prod
```

---

### Option 2: Full Deployment on Railway

**Deploy both frontend and backend** on Railway:

```bash
# Railway auto-detects and deploys both
railway init
railway up
```

Railway provides:
- ✅ 8GB RAM (enough for models)
- ✅ No cold starts (always-on containers)
- ✅ No size limits
- ✅ No execution timeouts
- ✅ $5 free credit monthly

---

### Option 3: Deploy on Render

**Render Free Tier** (good for demo):

1. **Create `render.yaml`** (already included)
2. **Connect GitHub repo** on Render dashboard
3. **Add environment variables**:
   - `GEMINI_API_KEY`
   - `USE_LLM=true`
   - `LLM_PROVIDER=gemini`

Render provides:
- ✅ Free tier (512MB RAM - might be tight)
- ✅ Auto-deploy from GitHub
- ✅ No cold starts
- ✅ Custom domains

---

## 🚫 Why Not Vercel for Backend?

| Requirement | Vercel | Railway | Render |
|-------------|---------|---------|---------|
| **Deployment Size** | 250MB max | No limit | No limit |
| **RAM** | 1-3GB | 8GB | 512MB-10GB |
| **Execution Time** | 10-30s | Unlimited | Unlimited |
| **Cold Starts** | Frequent | None | None |
| **Cost (Demo)** | Free | $5 credit | Free |
| **Suitable?** | ❌ No | ✅ Yes | ✅ Yes |

---

## 📝 Quick Start: Railway Deployment

### Backend:

1. **Create `railway.toml`** (optional, for config):
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "python api_server.py"
```

2. **Deploy**:
```bash
railway login
railway init
railway up
```

3. **Set environment variables** in Railway dashboard:
   - `GEMINI_API_KEY=your_key`
   - `USE_LLM=true`
   - `LLM_PROVIDER=gemini`
   - `ENV=production`

### Frontend (optional - if deploying separately):

1. **Update API URL** in `web/.env.production`:
```env
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

2. **Deploy to Vercel**:
```bash
cd web
vercel --prod
```

---

## 🎯 For Milestone 1 Submission

**Option 1**: Provide GitHub repository + demo video  
**Option 2**: Deploy to Railway and provide live link  
**Option 3**: Deploy frontend to Vercel + backend to Railway (best UX)

---

## 🔧 Environment Variables Needed

For any deployment platform, set these:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (with defaults)
USE_LLM=true
LLM_PROVIDER=gemini
ENV=production
PORT=8000
```

---

## 📊 Deployment Comparison

### Railway (Recommended):
- ✅ **Best for**: Full-stack RAG apps with ML models
- ✅ **Free tier**: $5 credit monthly
- ✅ **RAM**: 8GB available
- ✅ **Always-on**: No cold starts

### Render:
- ✅ **Best for**: Simple demos
- ⚠️ **Free tier**: 512MB RAM (tight for our app)
- ✅ **Easy setup**: Deploy from GitHub

### Vercel:
- ✅ **Best for**: Frontend only
- ❌ **Backend**: Not suitable for this RAG system
- ✅ **Free tier**: Unlimited bandwidth

---

## 🚀 Ready-to-Use Commands

### Deploy to Railway (Full Stack):
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Deploy Frontend Only to Vercel:
```bash
cd web
vercel --prod
```

---

**Recommendation**: Use Railway for backend, Vercel for frontend (if needed), or deploy both on Railway.

