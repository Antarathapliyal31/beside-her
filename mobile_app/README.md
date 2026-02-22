# 📱 Beside Her — Mobile App

React Native mobile app with Presage SmartSpectra contactless vital sensing.

---

## ⚡ Quick Start (3 steps)

### Step 1: Enter your API key

Open **`src/config.js`** and replace `PASTE_YOUR_API_KEY_HERE` with your Presage API key:

```js
export const PRESAGE_API_KEY = 'your_actual_key_here';
```

> Get your key from: https://physiology.presagetech.com

Also update `API_BASE_URL` if your Flask backend is running somewhere other than `http://10.0.2.2:5000`.

### Step 2: Install dependencies

```powershell
npm install
```

### Step 3: Run on your Android phone

Connect your phone via USB with USB debugging enabled, then:

```powershell
npx expo run:android
```

> ⚠️ Must use a **physical Android phone** — the camera SDK doesn't work on emulators.

That's it!

---

## 📁 Project Structure

```
beside-her-final/
│
├── src/
│   ├── config.js            ← ⭐ YOUR API KEY GOES HERE
│   ├── theme.js             ← Colors, fonts, spacing
│   │
│   ├── screens/
│   │   ├── LoginScreen.js
│   │   ├── SignupScreen.js
│   │   ├── MomCheckinScreen.js      ← Has "Scan My Vitals" button
│   │   ├── MomHistoryScreen.js
│   │   ├── PartnerDashboardScreen.js
│   │   ├── PartnerChatScreen.js
│   │   └── WeeklyReportScreen.js
│   │
│   ├── components/
│   │   ├── VitalsScanner.js         ← Presage SDK bridge (React Native side)
│   │   ├── EmojiScale.js
│   │   └── StatusBadge.js
│   │
│   ├── context/
│   │   └── AuthContext.js
│   │
│   └── services/
│       └── api.js                   ← All Flask API calls
│
├── android/                         ← Generated + modified for Presage
│   └── app/src/main/java/com/besideher/app/
│       ├── MainActivity.kt          ← Expo default
│       ├── MainApplication.kt       ← Modified: added SmartSpectraPackage
│       ├── SmartSpectraActivity.kt  ← Presage camera screen
│       ├── SmartSpectraModule.kt    ← React Native ↔ Native bridge
│       └── SmartSpectraPackage.kt   ← Registers module with RN
│
├── App.js                           ← Root navigation
├── app.json                         ← Expo config
└── package.json
```

---

## How the Vitals Scan Works

```
Mom taps "📷 Scan My Vitals" on check-in screen
      ↓
VitalsScanner.js opens modal → calls native module
      ↓
SmartSpectraActivity launches with Presage camera view
      ↓
User taps Presage's built-in measurement button
      ↓
30-second scan captures heart rate, breathing rate, HRV
      ↓
User taps "Done — Use Results"
      ↓
Results returned to React Native → sent with check-in to Flask API
      ↓
ML pipeline (mlanalysis.py) uses vitals for anomaly detection
```

---

## Running the Flask Backend

Your existing Flask app needs to be running for the mobile app to work:

```bash
cd beside-her
pip install -r requirements.txt
python app.py
```

If testing on a physical phone, both phone and PC must be on the same WiFi.
Find your PC's IP (`ipconfig`) and update `API_BASE_URL` in `src/config.js`:

```js
export const API_BASE_URL = 'http://192.168.1.xxx:5000';
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails with dependency errors | Run `cd android && .\gradlew.bat clean && cd ..` then rebuild |
| "Camera permission denied" | Must test on physical device, not emulator |
| "Could not reach server" | Check `API_BASE_URL` in `src/config.js` + Flask is running |
| Presage scan doesn't start | Verify your API key is correct in `src/config.js` |
| minSdk error | Already fixed (set to 26 in build.gradle) |
