import Foundation

// Mirrors the API's RankingsResponse / RankingEntry schemas
// (see src/api/schemas.py). Field names that differ from the JSON
// are mapped via CodingKeys below.

struct RankingsResponse: Codable {
    let week: Int
    let season: Int
    let rankings: [RankingEntry]
}

struct RankingEntry: Codable, Identifiable {
    let rank: Int
    let teamId: Int
    let teamName: String
    let conferenceName: String?
    let eloRating: Double
    let wins: Int
    let losses: Int

    // SwiftUI's List needs a stable id per row; team_id is unique.
    var id: Int { teamId }

    enum CodingKeys: String, CodingKey {
        case rank
        case teamId = "team_id"
        case teamName = "team_name"
        case conferenceName = "conference_name"
        case eloRating = "elo_rating"
        case wins, losses
    }
}
