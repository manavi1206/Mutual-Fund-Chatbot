# HDFC Mutual Fund FAQ Chatbot - Web UI

Next.js web application for the RAG-based HDFC Mutual Fund FAQ chatbot.

## Features

- 🎨 Groww-inspired design and color scheme
- 💬 Gemini-like chat interface
- ⚡ Fast and responsive
- 📱 Mobile-friendly
- 🔗 Source citations
- ⚠️ Conflict detection warnings

## Setup

1. Install dependencies:
```bash
npm install
```

2. Make sure Python dependencies are installed in parent directory:
```bash
cd ..
pip install -r requirements.txt
```

3. Set environment variables (if needed):
```bash
export GEMINI_API_KEY=your_key_here
```

4. Run development server:
```bash
npm run dev
```

## Deployment to Vercel

1. Push code to GitHub
2. Import project in Vercel
3. Set build settings:
   - Framework: Next.js
   - Root Directory: `web`
   - Build Command: `npm run build`
   - Install Command: `npm install`
4. Set environment variables:
   - `GEMINI_API_KEY`: Your Gemini API key
5. Deploy!

## Project Structure

```
web/
├── app/
│   ├── api/
│   │   └── query/
│   │       └── route.ts    # API endpoint
│   ├── globals.css         # Global styles
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Main chat page
│   └── page.module.css    # Component styles
├── package.json
├── next.config.js
└── vercel.json            # Vercel config
```

