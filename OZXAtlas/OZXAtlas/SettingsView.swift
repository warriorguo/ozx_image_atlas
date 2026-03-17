import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        Form {
            Section("Server") {
                TextField("Server URL", text: $appState.serverURL)
                    .textFieldStyle(.roundedBorder)
                Text("The remote address of the OZX Atlas web app")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Section("Save Directory") {
                HStack {
                    Text(appState.saveDirectory?.path ?? "Not set")
                        .foregroundColor(appState.saveDirectory != nil ? .primary : .secondary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                    Spacer()
                    Button("Choose...") {
                        appState.pickSaveDirectory()
                    }
                }
                Text("Exported atlas images will be saved here")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Section("Post-Export Agent") {
                TextField("Command", text: $appState.agentCommand)
                    .textFieldStyle(.roundedBorder)
                Text("Shell command to run after each export. The file path is appended as an argument.\nExample: python3 preprocess.py")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .frame(width: 480, height: 320)
        .padding()
    }
}
