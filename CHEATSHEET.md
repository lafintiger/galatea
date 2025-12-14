# 🌟 Galatea (Gala) - Command Cheatsheet

> Your Local Voice AI Companion

---

## ⌨️ Keyboard Shortcuts

| Key | Action | When |
|-----|--------|------|
| **Spacebar** (hold) | Push-to-talk | In PTT mode, when idle |
| **Spacebar** (release) | Send recording | While recording |
| **Escape** | Interrupt Gala | When she's speaking |
| **Ctrl + /** | Show help | Anytime |

---

## 🎙️ Voice Modes

| Mode | How It Works |
|------|--------------|
| **Push-to-Talk (PTT)** | Hold spacebar or mic button to record |
| **Open Mic (VAD)** | Auto-detects when you start/stop speaking |

---

## 🔍 Web Search

Say any of these to trigger a web search:

| Pattern | Example |
|---------|---------|
| "Search for..." | "Search for RTX 5090 specs" |
| "Look up..." | "Look up Python tutorials" |
| "Find out about..." | "Find out about quantum computing" |
| "Google..." | "Google best restaurants nearby" |
| "What is the latest..." | "What is the latest news on AI?" |

### Auto-Search Topics (always searches)
- Weather: "What's the weather?", "Will it rain tomorrow?"
- News: "What's happening in tech?", "Latest AI news"
- Prices: "How much does iPhone cost?", "Bitcoin price"
- Sports: "Who won the game?", "NBA standings"
- Products: "RTX 5090 specs", "Best laptop 2024"

---

## 👁️ Vision Commands

### Open/Close Eyes (Real-time Face Analysis)

| Command | Examples |
|---------|----------|
| **Open Eyes** | "Open your eyes", "Can you see me?", "Look at me" |
| **Close Eyes** | "Close your eyes", "Stop watching", "Don't look at me" |

### Screenshot/Image Analysis (One-time)

| Action | How |
|--------|-----|
| **Screenshot** | Click 👁️ button → "Screenshot" |
| **Upload Image** | Click 👁️ button → "Upload" |

### Quick Prompts for Images
- "What do you see?"
- "Read the text" (uses OCR model)
- "Describe this in detail"

---

## 📝 Workspace Commands

### Notes

| Command | Example |
|---------|---------|
| Add note | "Add note: Meeting tomorrow at 3pm" |
| | "Note this down: Call the dentist" |
| | "Remember this: Password is 1234" |
| Read notes | "Read my notes" |
| Open notes | "Open my workspace" |
| **Clear all notes** | "Clear my notes", "Delete all notes" |
| | "Wipe my notes", "Erase my notes" |

### Todos

| Command | Example |
|---------|---------|
| Add todo | "Add todo: Buy groceries" |
| | "Remind me to call mom" |
| | "I need to finish the report" |
| | "Task: Review the contract" |
| Mark done | "Mark 'buy groceries' as done" |
| | "Done with the report" |
| | "I finished calling mom" |
| Read todos | "What's on my todo list?" |
| **Clear all todos** | "Clear my todos", "Delete all my todos" |
| | "Wipe my todo list", "Empty my list" |

### Data Tracking

| Type | Command Examples |
|------|------------------|
| 🏃 **Exercise** | "Log 30 minutes running" |
| | "Log exercise 45 minutes" |
| | "Log 1 hour yoga" |
| ⚖️ **Weight** | "Log weight 185 lbs" |
| | "Log my weight 84 kg" |
| 🍎 **Diet** | "Track 2000 calories" |
| | "Log 500 calories" |
| 😴 **Sleep** | "Log sleep 8 hours" |
| | "Log 7 hours sleep" |
| 💧 **Water** | "Log water 64 oz" |
| | "Log 8 glasses water" |

---

## 🧠 Specialist Modes

Gala automatically switches to specialist models for certain topics:

| Domain | Triggers | Model |
|--------|----------|-------|
| 🏥 **Medical** | symptoms, medication, diagnosis | OpenBioLLM-8B |
| ⚖️ **Legal** | lawsuit, contract, rights | Qwen3-32B |
| 💻 **Coding** | code, debug, function | Qwen3-Coder-30B |
| 🔢 **Math** | calculate, equation, solve | Qwen2.5-Math-7B |
| 💰 **Finance** | invest, stock, budget | FinGPT-8B |
| 🔬 **Science** | physics, chemistry, biology | RNJ-1 |
| 🎨 **Creative** | story, poem, creative writing | Qwen3-32B |
| 📚 **Knowledge** | "be more knowledgeable", expert mode | GPT-OSS-20B |
| 💃 **Personality** | "bigger personality", "be sassy" | Dominique-24B |

---

## 💬 Conversation Management

| Action | How |
|--------|-----|
| **Clear conversation** | Click 🗑️ in transcript |
| **Export conversation** | Click ⬇️ dropdown → MD/TXT/JSON |
| **Save conversation** | Click 🕐 → "Save Current" |
| **Load conversation** | Click 🕐 → Select from list |
| **New conversation** | Click 🕐 → "New" |

---

## ⚙️ Settings (click ⚙️)

| Setting | Description |
|---------|-------------|
| **Model** | Choose Ollama LLM model |
| **Voice** | Select TTS voice (grouped by language) |
| **TTS Provider** | Piper (Fast) or Kokoro (HD) |
| **Voice Mode** | Push-to-Talk or Open Mic |
| **Transcript** | Show/hide conversation |
| **Auto-Search** | Let Gala search automatically |
| **Search Provider** | SearXNG or Perplexica |

---

## 🎨 UI Elements

| Icon | Location | Purpose |
|------|----------|---------|
| 👤 | Header | Profile & Onboarding |
| 🕐 | Header | Conversation History |
| ⚙️ | Header | Settings |
| 📝 | Header | Workspace Panel (pink when open) |
| 🎙️ | Center | Mic / Recording |
| 👁️ | Input bar | Vision (screenshot/webcam) |
| 🔍 | Input bar | Web Search |
| 👁️ (eye toggle) | Input bar | Open/Close Gala's eyes |

---

## 🌍 Supported Languages (Kokoro TTS)

| Flag | Language | Voice Prefix |
|------|----------|--------------|
| 🇺🇸 | English (US) | af_, am_ |
| 🇬🇧 | English (UK) | bf_, bm_ |
| 🇯🇵 | Japanese | jf_, jm_ |
| 🇨🇳 | Chinese | zf_, zm_ |
| 🇫🇷 | French | ff_ |
| 🇪🇸 | Spanish | ef_, em_ |
| 🇮🇹 | Italian | if_, im_ |
| 🇵🇹 | Portuguese | pf_, pm_ |
| 🇮🇳 | Hindi | hf_, hm_ |

---

## 🔒 Face Recognition & Access Control

| Role | Access Level |
|------|--------------|
| **Owner** | Full access - conversations, profile, history |
| **Friend/Family** | Can chat, no personal info shared |
| **Unknown** | Gala politely declines conversation |

### Enroll Faces
1. Click 👤 (Profile) in header
2. Go to "Face ID" tab
3. Use webcam to capture face
4. Owner enrolled first, then friends

---

## 📤 Export Formats

| Data | Formats |
|------|---------|
| **Conversation** | Markdown (.md), Text (.txt), JSON |
| **Notes** | Markdown (.md), Text (.txt) |
| **Todos** | Markdown (.md), JSON |
| **Tracked Data** | CSV, JSON |

---

## 🚀 Quick Tips

1. **Natural conversation** - Just talk normally, Gala understands context
2. **Interrupt anytime** - Press Escape to stop long responses
3. **Ask for searches** - If she doesn't know, ask her to search
4. **Track anything** - Use data logging for habits, exercise, diet
5. **Export regularly** - Backup your notes and data as files

---

*Galatea v1.0 - Your Local Voice AI Suite*
*100% Private - All processing on your machine*

