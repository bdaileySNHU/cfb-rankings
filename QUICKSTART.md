# College Football Ranking System - Quick Start Guide

A complete full-stack web application for ranking college football teams using a Modified ELO algorithm.

## 🚀 Quick Start (3 Steps)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Backend API
```bash
python3 main.py
```
API will run at: **http://localhost:8000**
- Interactive docs: http://localhost:8000/docs

### 3. Start the Frontend
```bash
cd frontend
python3 -m http.server 3000
```
Web app at: **http://localhost:3000**

## 📊 What You Get

### Backend (FastAPI + SQLite)
- ✅ Modified ELO ranking algorithm
- ✅ 20+ REST API endpoints
- ✅ Real-time ranking updates
- ✅ 33 teams with sample data
- ✅ 25 games across 2 weeks
- ✅ Historical ranking tracking
- ✅ Auto-generated API docs

### Frontend (HTML/CSS/JS)
- ✅ Rankings homepage with Top 25
- ✅ Team detail pages with stats
- ✅ All teams list (filterable)
- ✅ Games results viewer
- ✅ Responsive design
- ✅ Color-coded badges & indicators

## 🎯 Core Features

### Modified ELO Algorithm
**Preseason Ratings Based On:**
- 247Sports recruiting rankings (+0 to +200 pts)
- Transfer portal rankings (+0 to +100 pts)
- Returning production percentage (+0 to +40 pts)

**In-Season Updates:**
- Home field advantage: +65 points
- Margin of victory: Logarithmic multiplier (capped at 2.5)
- Conference adjustments: P5 vs G5 vs FCS
- Strength of schedule tracking

**Formula:**
```
New Rating = Old Rating + K × (Result - Expected) × MOV × Conference Multiplier

Where:
- K = 32 (volatility)
- Expected = 1 / (1 + 10^((Opp_Rating - Team_Rating) / 400))
- MOV = min(ln(point_diff + 1), 2.5)
```

## 📁 Project Structure

```
Stat-urday Synthesis/
├── Backend
│   ├── main.py              # FastAPI application
│   ├── models.py            # Database models
│   ├── schemas.py           # API schemas
│   ├── database.py          # DB configuration
│   ├── ranking_service.py   # ELO business logic
│   ├── cfb_elo_ranking.py   # Standalone algorithm
│   ├── seed_data.py         # Sample data generator
│   ├── demo.py              # Algorithm demo
│   └── cfb_rankings.db      # SQLite database
│
└── Frontend
    ├── index.html           # Rankings page
    ├── team.html            # Team details
    ├── teams.html           # All teams
    ├── games.html           # Game results
    ├── css/style.css        # Styles
    └── js/
        ├── api.js           # API service
        ├── app.js           # Homepage logic
        └── team.js          # Team page logic
```

## 🧪 Testing

### Test the Algorithm
```bash
python3 demo.py
```
Runs a simulation with sample teams and games.

### Test the API
```bash
# Get rankings
curl http://localhost:8000/api/rankings?limit=10

# Get team details
curl http://localhost:8000/api/teams/1

# Get system stats
curl http://localhost:8000/api/stats
```

### Test the Frontend
1. Start both backend and frontend
2. Navigate to http://localhost:3000
3. Click through:
   - Rankings table (sortable, clickable)
   - Team details (Georgia, Alabama, etc.)
   - All Teams (filter by conference)
   - Games (filter by week)

## 📊 Sample Data

The database comes pre-loaded with:
- **33 Teams**: Mix of P5, G5, and FCS
- **25 Games**: 2 weeks of results
- **Real Rankings**:
  1. Georgia (1869) - 2-0
  2. Ohio State (1850) - 2-0
  3. Alabama (1799) - 1-1 (quality loss!)

### Add More Data

**Add a new team:**
```bash
curl -X POST http://localhost:8000/api/teams \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tennessee",
    "conference": "P5",
    "recruiting_rank": 20,
    "transfer_rank": 30,
    "returning_production": 0.65
  }'
```

**Add a game (auto-updates rankings):**
```bash
curl -X POST http://localhost:8000/api/games \
  -H "Content-Type: application/json" \
  -d '{
    "home_team_id": 1,
    "away_team_id": 2,
    "home_score": 35,
    "away_score": 28,
    "week": 3,
    "season": 2024,
    "is_neutral_site": false
  }'
```

## 🔧 Configuration

### Change API Port
Edit `main.py` (bottom):
```python
uvicorn.run(app, host="0.0.0.0", port=9000)
```

### Change Frontend Port
```bash
python3 -m http.server 5000
```

### Point to Different API
Edit `frontend/js/api.js`:
```javascript
const API_BASE_URL = 'https://your-api.com/api';
```

## 🚢 Production Deployment

### Backend
1. Replace SQLite with PostgreSQL
2. Add environment variables
3. Deploy to Railway/Render/AWS
4. Update CORS origins

### Frontend
1. Update API URL in `api.js`
2. Deploy to Vercel/Netlify/GitHub Pages
3. Add custom domain

## 📖 Documentation

- **Backend API**: http://localhost:8000/docs
- **Algorithm Details**: See README.md
- **Frontend Docs**: See frontend/README.md

## 🎨 Customization

### Colors
Edit CSS variables in `frontend/css/style.css`

### Algorithm Parameters
Edit constants in `ranking_service.py`:
```python
K_FACTOR = 32              # Volatility
HOME_FIELD_ADVANTAGE = 65  # Home boost
MAX_MOV_MULTIPLIER = 2.5   # Blowout cap
```

### Ranking Criteria
Modify preseason bonuses in `ranking_service.py`:
- Recruiting bonuses (lines 30-45)
- Transfer bonuses (lines 47-55)
- Returning production (lines 57-65)

## 🐛 Troubleshooting

**API won't start:**
- Check if port 8000 is in use: `lsof -i :8000`
- Install dependencies: `pip install -r requirements.txt`

**Frontend not loading data:**
- Ensure API is running on port 8000
- Check browser console for CORS errors
- Verify API URL in `js/api.js`

**Database errors:**
- Delete `cfb_rankings.db` and run `python3 seed_data.py`

## 💡 Next Steps

1. **Integrate Real Data**: Use CollegeFootballData API
2. **Add Features**: Playoff odds, head-to-head, comparisons
3. **Visualizations**: Ranking charts with Chart.js
4. **Live Updates**: WebSockets for real-time games
5. **Mobile App**: React Native version

## 📝 License

MIT

## 🙏 Credits

Built with FastAPI, SQLAlchemy, and vanilla JavaScript.
Algorithm inspired by FiveThirtyEight's NFL ELO system.
