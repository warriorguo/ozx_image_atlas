import SwiftUI
import AppKit

class AppState: ObservableObject {
    static let defaultServerURL = "https://combineimg.local.playquota.com/"
    private static let defaults = UserDefaults(suiteName: "com.ozx.atlas.settings")!

    @Published var saveDirectory: URL? {
        didSet {
            if let url = saveDirectory {
                do {
                    let bookmark = try url.bookmarkData(
                        options: .withSecurityScope,
                        includingResourceValuesForKeys: nil,
                        relativeTo: nil
                    )
                    Self.defaults.set(bookmark, forKey: "saveDirectoryBookmark")
                    Self.defaults.set(url.path, forKey: "saveDirectoryPath")
                } catch {
                    print("Failed to create bookmark: \(error)")
                }
            }
        }
    }

    @Published var serverURL: String {
        didSet {
            Self.defaults.set(serverURL, forKey: "serverURL")
        }
    }

    @Published var agentCommand: String {
        didSet {
            Self.defaults.set(agentCommand, forKey: "agentCommand")
        }
    }

    @Published var statusMessage: String = ""

    init() {
        self.serverURL = Self.defaults.string(forKey: "serverURL") ?? Self.defaultServerURL
        self.agentCommand = Self.defaults.string(forKey: "agentCommand") ?? ""

        // Restore save directory from bookmark
        if let bookmarkData = Self.defaults.data(forKey: "saveDirectoryBookmark") {
            var isStale = false
            do {
                let url = try URL(
                    resolvingBookmarkData: bookmarkData,
                    options: .withSecurityScope,
                    relativeTo: nil,
                    bookmarkDataIsStale: &isStale
                )
                if url.startAccessingSecurityScopedResource() {
                    self.saveDirectory = url
                }
                if isStale {
                    // Re-create bookmark
                    self.saveDirectory = url
                }
            } catch {
                print("Failed to resolve bookmark: \(error)")
            }
        }
    }

    func pickSaveDirectory() {
        let panel = NSOpenPanel()
        panel.title = "Choose Save Directory"
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.canCreateDirectories = true
        panel.allowsMultipleSelection = false

        if let currentDir = saveDirectory {
            panel.directoryURL = currentDir
        }

        if panel.runModal() == .OK, let url = panel.url {
            saveDirectory = url
            statusMessage = "Save directory: \(url.path)"
        }
    }
}
