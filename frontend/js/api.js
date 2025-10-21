// API Service for College Football Ranking System

// Automatically detect API URL based on environment
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000/api'  // Local development
  : '/api';  // Production (uses same domain via Nginx proxy)

class ApiService {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async fetch(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  // Rankings
  async getRankings(limit = 25, season = null) {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (season) params.append('season', season.toString());
    return this.fetch(`/rankings?${params}`);
  }

  async getRankingHistory(teamId, season) {
    return this.fetch(`/rankings/history?team_id=${teamId}&season=${season}`);
  }

  async saveRankings(season, week) {
    return this.fetch('/rankings/save', {
      method: 'POST',
      body: JSON.stringify({ season, week }),
    });
  }

  // Teams
  async getTeams(conference = null, skip = 0, limit = 100) {
    const params = new URLSearchParams({ skip: skip.toString(), limit: limit.toString() });
    if (conference) params.append('conference', conference);
    return this.fetch(`/teams?${params}`);
  }

  async getTeam(teamId) {
    return this.fetch(`/teams/${teamId}`);
  }

  async createTeam(teamData) {
    return this.fetch('/teams', {
      method: 'POST',
      body: JSON.stringify(teamData),
    });
  }

  async updateTeam(teamId, teamData) {
    return this.fetch(`/teams/${teamId}`, {
      method: 'PUT',
      body: JSON.stringify(teamData),
    });
  }

  async getTeamSchedule(teamId, season) {
    return this.fetch(`/teams/${teamId}/schedule?season=${season}`);
  }

  // Games
  async getGames(filters = {}) {
    const params = new URLSearchParams();
    if (filters.season) params.append('season', filters.season.toString());
    if (filters.week !== undefined) params.append('week', filters.week.toString());
    if (filters.teamId) params.append('team_id', filters.teamId.toString());
    if (filters.processed !== undefined) params.append('processed', filters.processed.toString());
    if (filters.skip) params.append('skip', filters.skip.toString());
    if (filters.limit) params.append('limit', filters.limit.toString());

    return this.fetch(`/games?${params}`);
  }

  async getGame(gameId) {
    return this.fetch(`/games/${gameId}`);
  }

  async createGame(gameData) {
    return this.fetch('/games', {
      method: 'POST',
      body: JSON.stringify(gameData),
    });
  }

  // Seasons
  async getSeasons() {
    return this.fetch('/seasons');
  }

  async getActiveSeason() {
    try {
      const response = await this.fetch('/seasons/active');
      return response.year;
    } catch (error) {
      console.error('Failed to fetch active season:', error);
      // Fallback to current year
      return new Date().getFullYear();
    }
  }

  async createSeason(year) {
    return this.fetch('/seasons', {
      method: 'POST',
      body: JSON.stringify({ year }),
    });
  }

  async resetSeason(year) {
    return this.fetch(`/seasons/${year}/reset`, {
      method: 'POST',
    });
  }

  // Predictions
  async getPredictions(filters = {}) {
    const params = new URLSearchParams();
    if (filters.week !== undefined) params.append('week', filters.week.toString());
    if (filters.teamId) params.append('team_id', filters.teamId.toString());
    if (filters.nextWeek !== undefined) params.append('next_week', filters.nextWeek.toString());
    if (filters.season) params.append('season', filters.season.toString());

    return this.fetch(`/predictions?${params}`);
  }

  // Stats
  async getStats() {
    return this.fetch('/stats');
  }

  // Utility
  async recalculateRankings(season) {
    return this.fetch(`/calculate?season=${season}`, {
      method: 'POST',
    });
  }
}

// Export singleton instance
const api = new ApiService();
