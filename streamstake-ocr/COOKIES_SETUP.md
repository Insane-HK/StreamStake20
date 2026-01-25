# How to Export YouTube Cookies

To bypass the "Sign in to confirm you're not a bot" check in Headless mode, we need to feed the bot your actual browser cookies.

## Step 1: Install a Cookie Editor
Install the **"EditThisCookie"** (or similar) extension for Chrome/Edge:
- [Chrome Web Store Link](https://chromewebstore.google.com/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg)

## Step 2: Get the Cookies
1.  Go to **[YouTube.com](https://www.youtube.com)** and make sure you are **Signed In**.
2.  Click the **EditThisCookie** extension icon in your toolbar.
3.  Click the **Export** (Arrow pointing out/right) icon. 
    - This copies the cookies to your clipboard as JSON.

## Step 3: Save the File
1.  Create a new file in the `streamstake-ocr` folder named:
    `cookies.json`
    *(Full path: `d:\Coding\Projects\SERIOUS\Ai go\streamstake-ocr\cookies.json`)*
2.  **Paste** the clipboard content into this file.
3.  **Save** it.

## Step 4: Run
Once the file exists, run the script as usual:
```bash
python main.py --live
```
The script will now automatically load your identity and should skip the captcha/sign-in wall.
