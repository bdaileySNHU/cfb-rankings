import SwiftUI

// The base URL of your deployed API. Swap if your live domain differs.
private let apiBase = "https://cfb.bdailey.com"

struct ContentView: View {
    @State private var rankings: [RankingEntry] = []
    @State private var subtitle = "Loading…"

    var body: some View {
        NavigationStack {
            List(rankings) { team in
                HStack(spacing: 14) {
                    Text("\(team.rank)")
                        .font(.system(.body, design: .rounded).weight(.semibold))
                        .foregroundStyle(.secondary)
                        .frame(width: 28, alignment: .trailing)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(team.teamName).font(.headline)
                        Text(team.conferenceName ?? "—")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    VStack(alignment: .trailing, spacing: 2) {
                        Text(String(format: "%.0f", team.eloRating))
                            .font(.system(.body, design: .rounded))
                        Text("\(team.wins)-\(team.losses)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.vertical, 4)
            }
            .navigationTitle("Top 25")
            .task { await load() }
            .refreshable { await load() }
            .overlay(alignment: .bottom) {
                Text(subtitle)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .padding(8)
            }
        }
    }

    // Fetch + decode the Top 25 from the live API.
    func load() async {
        guard let url = URL(string: "\(apiBase)/api/rankings?limit=25") else { return }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            let decoded = try JSONDecoder().decode(RankingsResponse.self, from: data)
            rankings = decoded.rankings
            subtitle = "\(decoded.season) · Week \(decoded.week)"
        } catch {
            subtitle = "Error: \(error.localizedDescription)"
        }
    }
}

#Preview {
    ContentView()
}
