import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(spacing: 0) {
            // Toolbar
            HStack {
                // Save directory indicator
                HStack(spacing: 6) {
                    Image(systemName: "folder")
                        .foregroundColor(appState.saveDirectory != nil ? .green : .secondary)
                    Text(appState.saveDirectory?.lastPathComponent ?? "No save directory set")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }
                .onTapGesture {
                    appState.pickSaveDirectory()
                }
                .help("Click to change save directory (⇧⌘D)")

                Spacer()

                // Status message
                if !appState.statusMessage.isEmpty {
                    Text(appState.statusMessage)
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color(NSColor.controlBackgroundColor))

            Divider()

            // WebView
            AtlasWebView()
                .environmentObject(appState)
        }
    }
}
