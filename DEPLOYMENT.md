# 🚀 Easy Deployment Guide (Step-by-Step)

This guide will help you put your AI Chatbot on the internet so anyone can use it. We will use free services: **Render** for the Brain (Backend) and **Vercel** for the Website (Frontend).

---

## 🛠️ Phase 1: Upload Your Code to GitHub
Think of GitHub as a cloud storage for your code.
1.  **Create an Account:** Go to [github.com](https://github.com) and sign up.
2.  **Create a Repository:**
    -   Click the **+** icon in the top right -> **New repository**.
    -   Name it `my-ai-chatbot`.
    -   Click **Create repository**.
3.  **Upload Files:**
    -   Click **"uploading an existing file"** link on the next screen.
    -   Drag and drop your entire `ai-chatbot` folder contents into the browser.
    -   Click **Commit changes** (Green button).
    -   *Note: Make sure `backend/requirements.txt` is uploaded!*

---

## 🧠 Phase 2: Deploy the Brain (Backend)
We will use **Render** to run the Python server.
1.  **Go to Render:** Login at [render.com](https://render.com).
2.  **Create New Service:**
    -   Click **New +** button -> Select **Web Service**.
    -   Connect your GitHub account and select your `my-ai-chatbot` repository.
3.  **Configure Settings (Important!):**
    -   **Name:** Give it a name (e.g., `chatbot-backend`).
    -   **Root Directory:** Valid? Type: `backend`
    -   **Runtime:** Choose `Python 3`.
    -   **Build Command:** `pip install -r requirements.txt`
    -   **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
    -   **Instance Type:** Select "Free".
4.  **Add Secrets (Environment Variables):**
    -   Scroll down to "Environment Variables".
    -   Click **Add Environment Variable**:
        -   Key: `OPENROUTER_API_KEY`
        -   Value: `sk-or-v1-...` (Paste your actual API key here).
    -   Click **Add Environment Variable** again:
        -   Key: `ADMIN_PIN`
        -   Value: `2010` (Or whatever PIN you want).
5.  **Finish:** Click **Deploy Web Service**.
6.  **Wait:** It will take a few minutes. Once done, you will see a URL at the top left starting with `https://...`. **Copy this URL.** You will need it!

---

## 🎨 Phase 3: Connect the Website (Frontend)
Now we tell the website where the Brain is.
1.  **Open Code on PC:** Go to your `ai-chatbot/frontend` folder.
2.  **Edit script.js:** Open `script.js` with Notepad or VS Code.
3.  **Update URL:**
    -   Look at the top for `const CONFIG`.
    -   Change `apiEndpoint` to replace login `http://localhost:8000` with your **new Render URL** (from Phase 2).
    -   *Example:* `apiEndpoint: "https://chatbot-backend-xyz.onrender.com"`
4.  **Save** the file.
5.  **Re-upload to GitHub:** Go back to GitHub and upload the updated `script.js` to overwrite the old one.

---

## 🌐 Phase 4: Publish the Website
We will use **Vercel** to host the website HTML.
1.  **Go to Vercel:** Login at [vercel.com](https://vercel.com).
2.  **Add New Project:** Click **Add New...** -> **Project**.
3.  **Import Git:** Select your GitHub `my-ai-chatbot` repo and click **Import**.
4.  **Configure:**
    -   **Framework Preset:** Leave as "Other".
    -   **Root Directory:** Click "Edit" and select `frontend`.
5.  **Deploy:** Click the **Deploy** button.
6.  **Success!** You will get a link (e.g., `my-chatbot.vercel.app`). Share this link with your friends!

---

## 💻 Phase 5: Your Admin Panel
The Admin Panel is a special program that runs ONLY on your computer for security. It can control the cloud Brain properly.

1.  **Open Configuration:** Go to `ai-chatbot/admin-panel` on your PC.
2.  **Find Config File:** Look for `admin_config.json`. If it's not there, run the Admin Panel once and close it.
3.  **Edit Config:** Open `admin_config.json` with Notepad.
4.  **Update URL:** Change `"api_url"` to your **Render URL** (from Phase 2).
    ```json
    "api_url": "https://chatbot-backend-xyz.onrender.com"
    ```
5.  **Save.**
6.  Now when you open the Admin Panel app, it will show stats from your **Cloud Server** instead of your local one!

---

## ⚠️ Important Warning
Since you are using a Free plan on Render, the database (chat history) is **temporary**.
-   If the server restarts (which happens often on free plans), **chat history will be wiped**.
-   This is normal for free hosting with SQLite files.
-   To keep data forever, you would need to upgrade to a paid "Disk" plan on Render or use a proper database service.
