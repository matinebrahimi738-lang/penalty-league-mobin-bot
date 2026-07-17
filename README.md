# 🏆 Penalty League Mobin (PLM)

**A fully automated Telegram Penalty Shootout League Bot — written in Python 3.11 with Aiogram 3.13+**

---

## ✨ Features

- 🎮 **Full Penalty Shootout Gameplay** — 5-round matches with Sudden Death
- 🎲 **Rock-Paper-Scissors** — determines who shoots first
- ⚽ **Direction-based mechanics** — Left / Center / Right for shooter & goalkeeper
- 📊 **FORM display** — live visual progress (🟢🔴⚪)
- 🏆 **League table** — automatic ranking with points, GD, wins
- 📢 **Automatic channel publishing** — every event posted instantly
- 👥 **Player profiles** — stats, win rate, streaks, history
- ⚙️ **Admin panel** — full inline keyboard management
- 🔒 **Anti-cheat** — locks, role verification, duplicate-click prevention
- ⏰ **Timeouts** — auto-cancel if players don't respond
- 🌐 **Render-ready** — webhook + health check endpoint

---

## 🗂 Project Structure

```
telegram_bot/
├── main.py                  ← Entry point (polling + webhook)
├── config.py                ← Environment config
├── database.py              ← All SQLite queries (aiosqlite)
├── models.py                ← Enums, dataclasses, RPS logic
├── handlers/
│   ├── admin.py             ← Admin panel & match creation
│   ├── player.py            ← Player registration & panel
│   ├── match.py             ← Penalty direction callbacks
│   ├── rps.py               ← Rock-Paper-Scissors callbacks
│   ├── league.py            ← League table commands
│   └── channel.py           ← Manual channel post commands
├── services/
│   ├── match_engine.py      ← Core match orchestration
│   ├── league_service.py    ← League ranking logic
│   ├── player_service.py    ← Player business logic
│   └── channel_service.py   ← Telegram message publishing
└── utils/
    ├── keyboards.py         ← All InlineKeyboardMarkup builders
    ├── texts.py             ← All Persian text templates
    └── states.py            ← FSM StatesGroup definitions
```

---

## ⚙️ Setup

### 1. Clone & Install

```bash
git clone https://github.com/yourname/penalty-league-mobin.git
cd penalty-league-mobin
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
BOT_TOKEN=your_bot_token_from_BotFather
CHANNEL_ID=@your_channel_username
ADMIN_IDS=123456789,987654321
DATABASE_PATH=plm_database.db
MATCH_TIMEOUT=60
DEFAULT_ROUNDS=5
BOT_MODE=polling
```

### 3. Run (Development)

```bash
python -m telegram_bot.main
```

---

## 🚀 Deploy on Render

### Step-by-step

1. **Create a Render account** at [render.com](https://render.com)

2. **New Web Service** → connect your GitHub repo

3. **Build Command:**
   ```
   pip install -r requirements.txt
   ```

4. **Start Command:**
   ```
   python -m telegram_bot.main
   ```

5. **Environment Variables** (add in Render dashboard):

   | Key | Value |
   |-----|-------|
   | `BOT_TOKEN` | Your bot token |
   | `CHANNEL_ID` | `@yourchannel` |
   | `ADMIN_IDS` | `123456789` |
   | `DATABASE_PATH` | `plm_database.db` |
   | `BOT_MODE` | `webhook` |
   | `WEBHOOK_HOST` | `https://your-app.onrender.com` |
   | `WEBHOOK_PATH` | `/webhook` |
   | `WEBHOOK_PORT` | `10000` |

6. **Instance Type:** Free (or Starter for persistence)

> ⚠️ **Note:** Render free tier has ephemeral storage.  
> For a persistent database, use a paid instance with a persistent disk,  
> or set `DATABASE_PATH` to a mounted disk path.

---

## 🎮 How to Play

### For Players

1. Start the bot → `/start`
2. Choose your national team
3. Wait for an admin to create a match
4. Receive a private message when your match begins
5. Play Rock-Paper-Scissors to determine who shoots first
6. Choose direction each round: ⬅️ Left / ⬆️ Center / ➡️ Right
7. Results are published automatically to the channel

### For Admins

1. `/admin` → Open admin panel
2. **➕ مسابقه جدید** → Select Player 1 → Select Player 2 → Confirm
3. Match starts automatically!
4. Use **⛔ پایان مسابقه** to cancel an active match
5. **📢 ارسال اطلاعیه** → Broadcast to all players

---

## 📊 Scoring

| Event | Player Stat |
|-------|-------------|
| Shoot ≠ Save direction | ⚽ GOAL |
| Shoot = Save direction | 🧤 SAVE |
| Win match | +3 League points |
| Draw match | +1 League point |
| Loss | +0 League points |

### FORM Legend

| Symbol | Meaning |
|--------|---------|
| 🟢 | Goal scored (as shooter) |
| 🔴 | Shot saved (as shooter) |
| ⚪ | Round not yet played |

---

## 🔒 Security Features

- Role verification on every callback (shooter vs goalkeeper)
- Async locks per match (prevents race conditions)
- Duplicate-click protection (keyboard removed after choice)
- RPS and round timeouts (auto-cancel)
- Admin-only match creation and management
- Player registration required to interact

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11 |
| Bot Framework | Aiogram 3.13+ |
| Database | SQLite (aiosqlite) |
| Config | python-dotenv |
| HTTP Server | aiohttp (webhook mode) |
| Deployment | Render |

---

## 📝 Commands

| Command | Description |
|---------|-------------|
| `/start` | Open main panel |
| `/help` | Show help |
| `/stats` | View your stats |
| `/league` | View league table |
| `/table` | View league table |
| `/admin` | Open admin panel |
| `/post_league` | Post league to channel (admin) |
| `/post_message <text>` | Post custom message to channel (admin) |

---

## 📄 License

MIT License — Free to use and modify.

---

*Penalty League Mobin — Built with ⚽ and ❤️ in Python*
