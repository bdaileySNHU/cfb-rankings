# Project Documentation: College Football Ranking System

## 1. Project Overview

This project is a comprehensive college football ranking system that uses a modified ELO algorithm to rank teams. The system is designed to be a more accurate and nuanced measure of team strength than traditional polls, by taking into account factors such as recruiting rankings, transfer portal activity, and returning production.

The project includes a REST API backend built with FastAPI, which provides endpoints for accessing rankings, team information, game data, and more. The backend is integrated with a SQLite database for data persistence.

### Key Features:

*   **Modified ELO Algorithm:** A unique ranking algorithm that goes beyond simple win/loss records.
*   **Pre-season Ratings:** ELO ratings are seeded at the beginning of the season based on:
    *   247Sports recruiting class rankings
    *   Transfer portal rankings
    *   Returning production percentage
*   **In-Season Updates:** Rankings are updated after each game, with adjustments for:
    *   Home field advantage
    *   Margin of victory
    *   Conference strength (Power Five vs. Group of Five, FBS vs. FCS)
*   **Strength of Schedule:** The system calculates and considers the strength of each team's schedule.
*   **REST API:** A robust FastAPI backend provides a clean interface for accessing the ranking data.
*   **Real Data Integration:** The system can be populated with real game data from the College Football Data API.
*   **Historical Data:** The system stores and provides access to historical ranking data.

## 2. System Architecture

The system is composed of a frontend, a backend API, and a database.

*   **Frontend:** The frontend consists of static HTML, CSS, and JavaScript files. It provides a user interface for viewing rankings, teams, and game information. The frontend interacts with the backend API to retrieve and display data.
*   **Backend:** The backend is a REST API built with Python and the FastAPI framework. It implements the core logic of the ranking system, including the ELO algorithm, data processing, and API endpoints. 
*   **Database:** The system uses a SQLite database to store all data, including teams, games, and historical rankings. SQLAlchemy is used as the ORM for interacting with the database.

### Technologies Used:

*   **Backend:** Python, FastAPI, SQLAlchemy
*   **Database:** SQLite
*   **Frontend:** HTML, CSS, JavaScript

## 3. Backend API

The backend API is built with FastAPI and provides a comprehensive set of endpoints for interacting with the ranking system. The API is available at `http://localhost:8000` when running the application locally.

### Interactive API Documentation

FastAPI automatically generates interactive documentation, which is available at:

*   **Swagger UI**: `http://localhost:8000/docs`
*   **ReDoc**: `http://localhost:8000/redoc`

### API Endpoints

#### Rankings

*   `GET /api/rankings`: Get the current rankings.
    *   **Query Parameters:**
        *   `season` (int, optional): The season to get rankings for.
        *   `limit` (int, optional, default: 25): The number of teams to return.
    *   **Response Model:** `RankingsResponse`

*   `GET /api/rankings/history`: Get the historical rankings for a team.
    *   **Query Parameters:**
        *   `team_id` (int, required): The ID of the team.
        *   `season` (int, required): The season to get rankings for.
    *   **Response Model:** `List[RankingHistory]`

*   `POST /api/rankings/save`: Save the current rankings to the history.
    *   **Response Model:** `SuccessResponse`

#### Teams

*   `GET /api/teams`: Get a list of all teams.
    *   **Query Parameters:**
        *   `conference` (str, optional): Filter by conference.
        *   `skip` (int, optional, default: 0): The number of teams to skip.
        *   `limit` (int, optional, default: 100): The number of teams to return.
    *   **Response Model:** `List[Team]`

*   `GET /api/teams/{id}`: Get details for a specific team.
    *   **Response Model:** `TeamDetail`

*   `POST /api/teams`: Create a new team.
    *   **Request Model:** `TeamCreate`
    *   **Response Model:** `Team`

*   `PUT /api/teams/{id}`: Update an existing team.
    *   **Request Model:** `TeamUpdate`
    *   **Response Model:** `Team`

*   `GET /api/teams/{id}/schedule`: Get the schedule for a specific team.
    *   **Query Parameters:**
        *   `season` (int, required): The season to get the schedule for.
    *   **Response Model:** `TeamSchedule`

#### Games

*   `GET /api/games`: Get a list of games.
    *   **Query Parameters:**
        *   `season` (int, optional): Filter by season.
        *   `week` (int, optional): Filter by week.
        *   `team_id` (int, optional): Filter by team.
        *   `processed` (bool, optional): Filter by whether the game has been processed.
    *   **Response Model:** `List[Game]`

*   `GET /api/games/{id}`: Get details for a specific game.
    *   **Response Model:** `GameDetail`

*   `POST /api/games`: Add a new game. When a game is added, the rankings are automatically updated.
    *   **Request Model:** `GameCreate`
    *   **Response Model:** `GameResult`

#### Seasons

*   `GET /api/seasons`: Get a list of all seasons.
    *   **Response Model:** `List[SeasonResponse]`

*   `POST /api/seasons`: Create a new season.
    *   **Request Model:** `SeasonCreate`
    *   **Response Model:** `SeasonResponse`

*   `POST /api/seasons/{year}/reset`: Reset a season, which recalculates all preseason ratings.
    *   **Response Model:** `SuccessResponse`

#### Utility

*   `GET /api/stats`: Get system statistics.
    *   **Response Model:** `SystemStats`

*   `POST /api/calculate`: Recalculate all rankings from scratch for a given season.
    *   **Query Parameters:**
        *   `season` (int, required): The season to calculate rankings for.
    *   **Response Model:** `SuccessResponse`

*   `GET /`: Health check endpoint.
    *   **Response:** `{"message": "Hello from the CFB Rankings API!"}`

## 4. ELO Ranking Algorithm

The ranking system is based on a modified ELO algorithm. The ELO rating of a team is a measure of its strength. The rating is updated after each game based on the outcome and the opponent's rating.

### Preseason Rating Formula

At the beginning of each season, teams are assigned a preseason ELO rating. This rating is calculated based on the following factors:

*   **Base Rating:**
    *   FBS Teams: 1500
    *   FCS Teams: 1300
*   **Recruiting Bonus (based on 247Sports composite rank):**
    *   Top 5: +200
    *   Top 10: +150
    *   Top 25: +100
    *   Top 50: +50
    *   Top 75: +25
*   **Transfer Portal Bonus (based on 247Sports transfer portal rank):**
    *   Top 5: +100
    *   Top 10: +75
    *   Top 25: +50
    *   Top 50: +25
*   **Returning Production Bonus:**
    *   80%+: +40
    *   60-79%: +25
    *   40-59%: +10

### In-Season ELO Calculation

After each game, the ELO ratings of the two teams are updated based on the following formula:

`Expected Win Probability = 1 / (1 + 10^((Opponent_Rating - Team_Rating) / 400))`

`Rating Change = K * (Actual_Score - Expected_Score) * MOV_Multiplier * Conference_Multiplier`

Where:

*   `K` is the volatility factor, set to `32`.
*   `Actual_Score` is `1` for a win and `0` for a loss.
*   `Expected_Score` is the expected win probability.
*   `MOV_Multiplier` is the margin of victory multiplier.
*   `Conference_Multiplier` is a multiplier based on the conference of the two teams.

### Home Field Advantage

A home field advantage of `65` ELO points is added to the home team's rating for the purpose of calculating the expected outcome. This bonus is not permanently added to the team's rating.

### Margin of Victory Multiplier

The margin of victory (MOV) multiplier is used to give more weight to decisive wins. It is calculated as:

`MOV_Multiplier = ln(point_differential + 1)`

The multiplier is capped at a maximum value of `2.5`.

### Conference Multipliers

Conference multipliers are used to account for the difference in strength between conferences.

*   **P5 vs G5:**
    *   P5 beats G5: 0.9x (less gain for the P5 team)
    *   G5 beats P5: 1.1x (upset bonus for the G5 team)
*   **FBS vs FCS:**
    *   FBS beats FCS: 0.5x (minimal gain for the FBS team)
    *   FCS beats FBS: 2.0x (major upset bonus for the FCS team)

## 5. Database Schema

The database schema is defined using SQLAlchemy ORM. It consists of the following models:

### Team

The `Team` model represents a college football team.

*   `id` (Integer, Primary Key)
*   `name` (String, Unique)
*   `conference` (Enum: `P5`, `G5`, `FCS`)
*   `recruiting_rank` (Integer)
*   `transfer_rank` (Integer)
*   `returning_production` (Float)
*   `elo_rating` (Float)
*   `initial_rating` (Float)
*   `wins` (Integer)
*   `losses` (Integer)
*   `created_at` (DateTime)
*   `updated_at` (DateTime)

**Relationships:**

*   `home_games`: One-to-many relationship with the `Game` model (as home team).
*   `away_games`: One-to-many relationship with the `Game` model (as away team).
*   `ranking_history`: One-to-many relationship with the `RankingHistory` model.

### Game

The `Game` model represents a single game between two teams.

*   `id` (Integer, Primary Key)
*   `home_team_id` (Integer, Foreign Key to `teams.id`)
*   `away_team_id` (Integer, Foreign Key to `teams.id`)
*   `home_score` (Integer)
*   `away_score` (Integer)
*   `week` (Integer)
*   `season` (Integer)
*   `is_neutral_site` (Boolean)
*   `game_date` (DateTime)
*   `is_processed` (Boolean)
*   `home_rating_change` (Float)
*   `away_rating_change` (Float)
*   `created_at` (DateTime)

**Relationships:**

*   `home_team`: Many-to-one relationship with the `Team` model.
*   `away_team`: Many-to-one relationship with the `Team` model.

### RankingHistory

The `RankingHistory` model stores the historical rankings of each team on a weekly basis.

*   `id` (Integer, Primary Key)
*   `team_id` (Integer, Foreign Key to `teams.id`)
*   `week` (Integer)
*   `season` (Integer)
*   `rank` (Integer)
*   `elo_rating` (Float)
*   `wins` (Integer)
*   `losses` (Integer)
*   `sos` (Float)
*   `sos_rank` (Integer)
*   `created_at` (DateTime)

**Relationships:**

*   `team`: Many-to-one relationship with the `Team` model.

### Season

The `Season` model stores metadata for each season.

*   `id` (Integer, Primary Key)
*   `year` (Integer, Unique)
*   `current_week` (Integer)
*   `is_active` (Boolean)
*   `created_at` (DateTime)
*   `updated_at` (DateTime)

## 6. Getting Started

### Prerequisites

*   Python 3.11+
*   pip

### Setup

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Initialize the database with sample data:**
    ```bash
    python3 seed_data.py
    ```

3.  **Start the API server:**
    ```bash
    python3 main.py
    ```

    The server will be available at `http://localhost:8000`.

### Real Data Integration

To use real data from the College Football Data API, you need to get a free API key from `https://collegefootballdata.com/key`.

1.  **Set the API key as an environment variable:**
    ```bash
    export CFBD_API_KEY='your-key-here'
    ```

2.  **Import the real data:**
    ```bash
    python3 import_real_data.py
    ```

## 7. Deployment

This project can be deployed to a VPS with a subdomain. The `DEPLOYMENT.md` file provides a detailed guide for deploying the application to an Ubuntu/Debian VPS.

The deployment architecture consists of:

*   **Nginx:** As a reverse proxy to handle incoming traffic and serve static files.
*   **Gunicorn:** As a WSGI server to run the FastAPI application.
*   **Systemd:** To manage the Gunicorn process as a service.
*   **Certbot:** To obtain and manage SSL certificates.

The `deploy/` directory contains the necessary scripts and configuration files for deployment:

*   `setup.sh`: A script to install all the necessary dependencies and configure the server.
*   `deploy.sh`: A script to pull the latest changes from the git repository and restart the application.
*   `nginx.conf`: A template for the Nginx configuration file.
*   `cfb-rankings.service`: A template for the systemd service file.

For detailed instructions, please refer to the `DEPLOYMENT.md` file.