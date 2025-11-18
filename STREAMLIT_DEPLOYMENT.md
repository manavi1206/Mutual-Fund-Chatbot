# 🚀 Streamlit Deployment Guide

## ✅ Setup Complete!

Your HDFC Mutual Fund FAQ Assistant is now ready to deploy to Streamlit Cloud!

---

## 🖥️ Test Locally (Optional)

Before deploying, test it locally:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run Streamlit
streamlit run streamlit_app.py
```

**Open**: http://localhost:8501

---

## ☁️ Deploy to Streamlit Cloud (3 Minutes)

### Step 1: Go to Streamlit Cloud

Visit: **[share.streamlit.io](https://share.streamlit.io)**

### Step 2: Sign In

- Click **"Sign in with GitHub"**
- Authorize Streamlit to access your repositories

### Step 3: Create New App

1. Click **"New app"** button
2. Fill in the details:

   **Repository**: `manavi1206/Mutual-Fund-Chatbot`  
   **Branch**: `main`  
   **Main file path**: `streamlit_app.py`

### Step 4: Add Secrets (Important!)

Click **"Advanced settings"** → **"Secrets"**

Add this:
```toml
GEMINI_API_KEY = "your_gemini_api_key_here"
USE_LLM = "true"
LLM_PROVIDER = "gemini"
```

**⚠️ Replace** `your_gemini_api_key_here` with your actual Gemini API key!

### Step 5: Deploy!

Click **"Deploy"** button

⏳ Deployment takes 5-10 minutes (installing dependencies + loading models)

---

## 🎉 Your App is Live!

Once deployed, you'll get a URL like:

**`https://your-app-name.streamlit.app`**

Share this link with anyone! No authentication needed for viewing.

---

## 📊 What Gets Deployed

✅ Complete RAG system with 1,886 vectors  
✅ FAISS index and embeddings  
✅ All 26 source documents  
✅ Sentence transformer models  
✅ Gemini LLM integration  
✅ Beautiful Groww-inspired UI  

**Total deployment size**: ~500MB  
**RAM usage**: 3-4GB (Streamlit provides 8GB free)  
**Cold start**: ~10 seconds on first load

---

## 🔧 Troubleshooting

### Issue: "ModuleNotFoundError"
**Solution**: Make sure `requirements.txt` is in the root directory (it is!)

### Issue: "GEMINI_API_KEY not found"
**Solution**: Double-check you added secrets in Step 4

### Issue: "Out of memory"
**Solution**: Streamlit free tier has 8GB RAM - should be enough. If not, upgrade to paid tier or optimize models.

### Issue: App takes long to load
**Solution**: First load is slow (10s) while loading models. Subsequent loads are fast due to caching.

---

## 📝 For Milestone 1 Submission

Once deployed, you can provide:

1. ✅ **GitHub Repository**: https://github.com/manavi1206/Mutual-Fund-Chatbot
2. ✅ **Live Demo**: https://your-app-name.streamlit.app
3. ✅ **Source List**: In `sources.csv`
4. ✅ **Sample Q&A**: In `SAMPLE_QA.md`
5. ✅ **README**: Complete setup guide
6. ✅ **Checklist**: In `MILESTONE_CHECKLIST.md`

**All deliverables complete!** 🎓

---

## 🎨 Features Included

### UI Features:
- ✅ Chat-based interface with message history
- ✅ 8 example questions in sidebar
- ✅ Clear chat button
- ✅ Source links with each answer
- ✅ Loading states and error handling
- ✅ Groww-inspired color scheme (green: #00d09c)
- ✅ Responsive design
- ✅ Facts-only disclaimer

### Technical Features:
- ✅ RAG with FAISS vector search
- ✅ Gemini LLM for answer generation
- ✅ Clarification handling for ambiguous queries
- ✅ Context tracking across conversation
- ✅ Source citation with URLs
- ✅ Investment advice refusal
- ✅ Direct answers for simple metrics
- ✅ Proper formatting (₹, %, etc.)

---

## 💡 Tips for Demo

When presenting your app:

1. **Start with examples**: Click sidebar buttons to show different query types
2. **Show clarification**: Try "minimum SIP" → bot asks which fund
3. **Test context**: Ask "expense ratio" for a fund, then "exit load" (remembers fund)
4. **Show refusal**: Try "should I invest?" → polite refusal
5. **Check sources**: Click source links to verify factual accuracy

---

## 📊 Monitoring Your App

In Streamlit Cloud dashboard:

- **Logs**: View real-time application logs
- **Analytics**: See visitor count and usage
- **Secrets**: Update API keys without redeploying
- **Reboot**: Restart app if needed

---

## 🔒 Security Notes

✅ API keys stored securely in Streamlit secrets  
✅ Not committed to GitHub (.gitignore)  
✅ No PII collected from users  
✅ Source citations for transparency  
✅ Read-only access to data sources  

---

## 📞 Support

If you encounter issues:

1. Check Streamlit Cloud logs
2. Verify secrets are correctly set
3. Ensure Gemini API key is valid
4. Review `requirements.txt` for missing dependencies

---

**🚀 Ready to Deploy!**

Your repository is at: https://github.com/manavi1206/Mutual-Fund-Chatbot  
Local test: `streamlit run streamlit_app.py`  
Deploy: [share.streamlit.io](https://share.streamlit.io)

**Good luck with your Milestone 1 submission!** 🎓

