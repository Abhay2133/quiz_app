# QUIZ APPLICATION - README
**For Prashan Baan Competition**

**Status:** ✅ **PRODUCTION READY** (v1.0 - December 31, 2025)

A lightweight, fully offline Python quiz application for competitions. Participants connect to an admin machine via local WiFi/hotspot network using native sockets. No internet required!

## Quick Start (30 seconds)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Admin (on host machine with WiFi/hotspot enabled)
python3 admin.py

# 3. Start Participants (on client machines on same WiFi)
python3 participant.py
```

## Key Features

✅ **Offline Competition** - Works over local WiFi/hotspot (no internet needed)  
✅ **Real-time Scoring** - Live scoreboard with instant updates  
✅ **4 Quiz Rounds** - Different question types and difficulty levels  
✅ **Multi-Participant** - Support for up to 50 participants  
✅ **Buzzer System** - Round 4 includes buzzer-based questions  
✅ **Admin Dashboard** - Full control over rounds, questions, scoring  
✅ **Network Sync** - All participants synchronized with admin  

## Requirements

- **Python 3.8+** (on all machines)
- **Local Network** - All devices on same WiFi/hotspot
- **Port 4040** - Available on admin machine
- **Dependencies** - Listed in [requirements.txt](requirements.txt)

## Installation

### Option 1: Virtual Environment (Recommended)

```bash
# Clone/Download project
cd quiz_app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "from app.admin import main; print('✓ Ready to go!')"
```

### Option 2: Direct Install

```bash
pip install -r requirements.txt
```

## Running the Application

### Admin Interface

**On host machine (with WiFi/hotspot enabled):**

```bash
python3 admin.py
```

The Admin interface will:
- Auto-detect WiFi IP address
- Start server on port 4040
- Display UI for managing rounds and participants
- Show live scoreboard

### Participant Interface

**On client machines (connected to same WiFi):**

```bash
python3 participant.py
```

Participants will:
- Enter their name
- Connect to admin's IP address
- Receive questions automatically
- Submit answers in real-time
- See their scores update

## Important Files & Directories

```
quiz_app/
├── admin.py                    # Admin entry point ⭐
├── participant.py              # Participant entry point ⭐
├── config.json                 # Configuration (port, timeouts, etc.)
├── requirements.txt            # Python dependencies
├── FINAL_DOCUMENTATION.md      # Complete documentation 📖
│
├── app/
│   ├── admin.py               # Admin logic
│   ├── user.py                # Participant logic
│   ├── lib/
│   │   ├── qb.py             # Question Bank (CSV loading)
│   │   ├── sockets.py        # Network communication
│   │   └── validators.py     # Data validation
│   └── ui/
│       ├── admin/            # Admin UI
│       ├── user/             # Participant UI
│       └── rounds/           # Round implementations
│
├── data/
│   ├── questions/
│   │   ├── r1.csv           # Round 1 (10 questions)
│   │   ├── r2.csv           # Round 2 (8 questions)
│   │   ├── r3.csv           # Round 3 (9 questions)
│   │   └── r4.csv           # Round 4 (10 questions)
│   └── icons/               # UI icons
│
└── logs/                      # Application logs
```


## CSV Question Format

Questions are stored in CSV files with this format:

```csv
qid,text,options,answer,imgPath
1,What does CPU stand for?,Option1|Option2|Option3|Option4,1,
2,Another question?,OptionA|OptionB|OptionC|OptionD,3,image.avif
```

**CSV Columns:**
- `qid`: Question ID (1, 2, 3, ...)
- `text`: Question text
- `options`: Pipe-separated (`|`) answer options
- `answer`: Correct answer index (1-4)
- `imgPath`: Image file (optional, in `data/questions/imgs/`)

## Configuration

Edit `config.json` to customize:

```json
{
  "network": {
    "port": 4040,           # Server port
    "timeout": 30,          # Connection timeout
    "max_reconnect_attempts": 5
  },
  "rounds": {
    "round1": {"mark": 10, "name": "Straight Forward"},
    "round2": {"mark": 10, "name": "Bujho Toh Jano"},
    "round3": {"mark": 10, "name": "Roll the Dice"},
    "round4": {"mark": 10, "name": "Speedo Round"}
  },
  "quiz": {
    "min_participants": 1,
    "max_participants": 50
  }
}
```

## Troubleshooting

### "Could not detect WiFi IP address"
- ✅ Enable WiFi on admin machine
- ✅ Or create personal hotspot
- ✅ Check network settings

### "Connection failed with error 36"
- ✅ This is handled automatically on macOS
- ✅ Ensure port 4040 is available
- ✅ Check firewall settings

### "Options not displaying correctly"
- ✅ Verify CSV uses pipe separator (`|`) not comma
- ✅ Check answer index is 1-4
- ✅ Ensure 2-4 options per question

### "Port already in use"
- ✅ Change port in `config.json`
- ✅ Or kill process: `lsof -ti:4040 | xargs kill -9`

### Network Connection Issues
1. Verify both machines on same WiFi
2. Check firewall allows connections
3. Review logs in `logs/` directory
4. Verify magic_key in config.json

## Features by Round

| Round | Type | Questions | Key Feature |
|-------|------|-----------|------------|
| 1 | Multiple Choice | 10 | Standard MCQ format |
| 2 | Timed MCQ | 8 | Time-based questions |
| 3 | Image-based | 9 | Questions with images |
| 4 | Buzzer Round | 10 | Fastest finger wins |

## Deployment

**For Complete Deployment Instructions, see [FINAL_DOCUMENTATION.md](FINAL_DOCUMENTATION.md)**

### Quick Checklist

- [ ] Python 3.8+ installed
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] WiFi/Hotspot enabled on admin machine
- [ ] Port 4040 available
- [ ] CSV files in `data/questions/`
- [ ] `logs/` directory exists

### Deploy Steps

1. **Prepare Admin Machine**
   ```bash
   cd quiz_app
   python3 admin.py
   ```

2. **Connect Participants**
   ```bash
   cd quiz_app
   python3 participant.py
   ```

3. **Start Quiz** - Click "Start Quiz" in admin UI

4. **Manage Rounds** - Admin controls progression

5. **View Results** - Completion popup shows final scores

## Recent Fixes (v1.0)

✅ CSV data validation and encoding support  
✅ macOS socket error 36 (EINPROGRESS) handling  
✅ Round4 options display synchronization  
✅ Quiz completion popup messages  
✅ Multi-encoding CSV file support  
✅ Network communication optimization  

## Documentation

📖 **For comprehensive documentation including:**
- Architecture details
- Bug fixes and improvements
- Troubleshooting guide
- Known limitations
- Installation troubleshooting

**See:** [FINAL_DOCUMENTATION.md](FINAL_DOCUMENTATION.md)

## Version Info

- **Version:** 1.0 (Production Release)
- **Date:** December 31, 2025
- **Status:** ✅ Ready for Deployment
- **Python:** 3.8+
- **License:** As per project

## Getting Help

1. **Check FINAL_DOCUMENTATION.md** - Comprehensive guide
2. **Review config.json** - Verify settings
3. **Check logs/** - Review application logs
4. **Verify network** - Ensure WiFi connectivity
5. **Test imports** - `python3 -c "from app.admin import main"`

## Contact & Support

For issues:
1. Review FINAL_DOCUMENTATION.md troubleshooting section
2. Check application logs in `logs/` directory
3. Verify network connectivity
4. Ensure all dependencies installed

---

**Happy Quizzing! 🎉**

**Questions? See [FINAL_DOCUMENTATION.md](FINAL_DOCUMENTATION.md) for complete guide.**
