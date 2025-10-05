# College Football Ranking System - Frontend

A clean, responsive web interface for the College Football Modified ELO Ranking System.

## Features

### Pages

1. **Rankings (index.html)**
   - Top 25 (or more) current rankings
   - Live system statistics
   - Color-coded rank badges
   - Conference indicators (P5, G5, FCS)
   - Strength of Schedule visualization
   - Click any team to view details

2. **Team Details (team.html)**
   - Complete team profile
   - Current ELO rating and rank
   - Preseason factors (recruiting, transfers, returning production)
   - Full season schedule with results
   - Head-to-head clickable opponents

3. **All Teams (teams.html)**
   - Comprehensive team list
   - Filter by conference
   - Sortable by ELO rating
   - Quick access to all team pages

4. **Games (games.html)**
   - All game results
   - Filter by week
   - Shows winners, scores, and ELO changes
   - Neutral site indicators

## Running the Frontend

### Prerequisites
- Python 3.11+ (for simple HTTP server)
- API backend running on `http://localhost:8000`

### Start the Frontend

```bash
# Navigate to frontend directory
cd frontend

# Start simple HTTP server
python3 -m http.server 3000
```

Then open your browser to: **http://localhost:3000**

### Start Both Backend and Frontend

```bash
# Terminal 1: Start API
python3 main.py

# Terminal 2: Start Frontend
cd frontend && python3 -m http.server 3000
```

## Technology Stack

- **HTML5** - Semantic markup
- **CSS3** - Custom styling with CSS variables
- **Vanilla JavaScript** - No frameworks, lightweight
- **Fetch API** - RESTful API communication

## Features

### Responsive Design
- Mobile-first approach
- Works on phones, tablets, and desktops
- Collapsible navigation on mobile

### Visual Elements
- **Rank Badges**: Gold (Top 5), Silver (Top 10), Bronze (Top 25)
- **Conference Badges**: Blue (P5), Green (G5), Gray (FCS)
- **SOS Indicators**: Color-coded difficulty dots
- **Interactive Tables**: Hover effects, clickable rows
- **Loading States**: Spinners while data loads
- **Error Handling**: User-friendly error messages

### Color Scheme
- Primary: Navy Blue (`#1a365d`)
- Secondary: Royal Blue (`#2c5282`)
- Accent: Gold (`#d69e2e`)
- Success: Green (`#38a169`)
- Danger: Red (`#e53e3e`)

## File Structure

```
frontend/
├── index.html          # Rankings homepage
├── team.html           # Team detail page
├── teams.html          # All teams list
├── games.html          # Games results
├── css/
│   └── style.css       # Main stylesheet
└── js/
    ├── api.js          # API service layer
    ├── app.js          # Homepage logic
    └── team.js         # Team page logic
```

## API Configuration

The API base URL is configured in `js/api.js`:

```javascript
const API_BASE_URL = 'http://localhost:8000/api';
```

For production, update this to your deployed API URL.

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Customization

### Colors
Edit CSS variables in `css/style.css`:

```css
:root {
  --primary-color: #1a365d;
  --accent-color: #d69e2e;
  /* ... */
}
```

### API Endpoint
Edit in `js/api.js`:

```javascript
const API_BASE_URL = 'https://your-api.com/api';
```

## Performance

- **Lightweight**: ~30KB total (uncompressed)
- **Fast**: No build process, instant reload
- **Efficient**: Parallel API calls where possible

## Future Enhancements

- [ ] Add ranking history charts (Chart.js)
- [ ] Live game updates (WebSockets)
- [ ] Team comparison tool
- [ ] Playoff probability calculator
- [ ] Export rankings to CSV/PDF
- [ ] Dark mode toggle
- [ ] Team logo integration

## License

MIT
