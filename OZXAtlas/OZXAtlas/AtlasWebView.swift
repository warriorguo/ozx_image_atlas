import SwiftUI
import WebKit

struct AtlasWebView: NSViewRepresentable {
    @EnvironmentObject var appState: AppState

    func makeCoordinator() -> Coordinator {
        Coordinator(appState: appState)
    }

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()

        // Register JS → Swift message handlers
        let userContentController = WKUserContentController()
        userContentController.add(context.coordinator, name: "nativeSave")
        userContentController.add(context.coordinator, name: "nativeAgent")
        userContentController.add(context.coordinator, name: "nativePickDirectory")

        // Inject bridge script that intercepts export
        let bridgeScript = WKUserScript(
            source: Self.bridgeJS,
            injectionTime: .atDocumentEnd,
            forMainFrameOnly: true
        )
        userContentController.addUserScript(bridgeScript)

        config.userContentController = userContentController

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        context.coordinator.webView = webView

        // Load the remote server
        if let url = URL(string: appState.serverURL) {
            webView.load(URLRequest(url: url))
        }

        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        context.coordinator.appState = appState
    }

    // JavaScript bridge injected into the web page
    static let bridgeJS = """
    (function() {
        // Check if running inside native app
        window.isNativeApp = true;

        // Override the export function's download behavior
        // We intercept <a> element clicks with download attribute
        const originalCreateElement = document.createElement.bind(document);
        document.createElement = function(tagName) {
            const el = originalCreateElement(tagName);
            if (tagName.toLowerCase() === 'a') {
                const originalClick = el.click.bind(el);
                el.click = function() {
                    if (el.download && el.href && el.href.startsWith('blob:')) {
                        // Intercept download: fetch blob and send to native
                        fetch(el.href)
                            .then(r => r.blob())
                            .then(blob => blob.arrayBuffer())
                            .then(buffer => {
                                const base64 = btoa(
                                    new Uint8Array(buffer)
                                        .reduce((data, byte) => data + String.fromCharCode(byte), '')
                                );
                                window.webkit.messageHandlers.nativeSave.postMessage({
                                    filename: el.download,
                                    data: base64
                                });
                            })
                            .catch(err => {
                                console.error('Native save failed, falling back to download:', err);
                                originalClick();
                            });
                    } else {
                        originalClick();
                    }
                };
            }
            return el;
        };

        console.log('[OZXAtlas] Native bridge initialized');
    })();
    """

    // MARK: - Coordinator

    class Coordinator: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
        var appState: AppState
        weak var webView: WKWebView?

        init(appState: AppState) {
            self.appState = appState
        }

        func userContentController(
            _ userContentController: WKUserContentController,
            didReceive message: WKScriptMessage
        ) {
            switch message.name {
            case "nativeSave":
                handleSave(message: message)
            case "nativeAgent":
                handleAgent(message: message)
            case "nativePickDirectory":
                DispatchQueue.main.async {
                    self.appState.pickSaveDirectory()
                }
            default:
                break
            }
        }

        private func handleSave(message: WKScriptMessage) {
            guard let body = message.body as? [String: Any],
                  let filename = body["filename"] as? String,
                  let base64String = body["data"] as? String,
                  let data = Data(base64Encoded: base64String)
            else {
                updateStatus("Save failed: invalid data")
                return
            }

            guard let saveDir = appState.saveDirectory else {
                // No directory set — prompt user to pick one, then save
                DispatchQueue.main.async {
                    self.appState.pickSaveDirectory()
                    // Try again after picking
                    if let dir = self.appState.saveDirectory {
                        self.saveFile(data: data, filename: filename, directory: dir)
                    }
                }
                return
            }

            saveFile(data: data, filename: filename, directory: saveDir)
        }

        private func saveFile(data: Data, filename: String, directory: URL) {
            let fileURL = directory.appendingPathComponent(filename)

            do {
                try data.write(to: fileURL)
                updateStatus("Saved: \(fileURL.path)")
                notifyWebView(success: true, path: fileURL.path)

                // Run agent if configured
                if !appState.agentCommand.isEmpty {
                    runAgent(filePath: fileURL.path)
                }
            } catch {
                updateStatus("Save failed: \(error.localizedDescription)")
                notifyWebView(success: false, path: "")
            }
        }

        private func handleAgent(message: WKScriptMessage) {
            guard let body = message.body as? [String: Any],
                  let command = body["command"] as? String
            else { return }

            let args = body["args"] as? [String] ?? []
            runAgentCommand(command: command, args: args)
        }

        private func runAgent(filePath: String) {
            let command = appState.agentCommand
            guard !command.isEmpty else { return }

            updateStatus("Running agent...")

            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: "/bin/zsh")
                process.arguments = ["-c", "\(command) \"\(filePath)\""]
                process.currentDirectoryURL = self.appState.saveDirectory

                let pipe = Pipe()
                process.standardOutput = pipe
                process.standardError = pipe

                do {
                    try process.run()
                    process.waitUntilExit()

                    let output = String(
                        data: pipe.fileHandleForReading.readDataToEndOfFile(),
                        encoding: .utf8
                    ) ?? ""

                    DispatchQueue.main.async {
                        if process.terminationStatus == 0 {
                            self.updateStatus("Agent completed: \(output.prefix(100))")
                        } else {
                            self.updateStatus("Agent failed (exit \(process.terminationStatus))")
                        }
                    }
                } catch {
                    DispatchQueue.main.async {
                        self.updateStatus("Agent error: \(error.localizedDescription)")
                    }
                }
            }
        }

        private func runAgentCommand(command: String, args: [String]) {
            updateStatus("Running: \(command)...")

            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: "/bin/zsh")
                let fullCommand = ([command] + args).joined(separator: " ")
                process.arguments = ["-c", fullCommand]
                process.currentDirectoryURL = self.appState.saveDirectory

                let pipe = Pipe()
                process.standardOutput = pipe
                process.standardError = pipe

                do {
                    try process.run()
                    process.waitUntilExit()

                    let output = String(
                        data: pipe.fileHandleForReading.readDataToEndOfFile(),
                        encoding: .utf8
                    ) ?? ""

                    DispatchQueue.main.async {
                        self.updateStatus(process.terminationStatus == 0
                            ? "Done: \(output.prefix(80))"
                            : "Failed (exit \(process.terminationStatus))")
                    }
                } catch {
                    DispatchQueue.main.async {
                        self.updateStatus("Error: \(error.localizedDescription)")
                    }
                }
            }
        }

        private func updateStatus(_ message: String) {
            DispatchQueue.main.async {
                self.appState.statusMessage = message
            }
        }

        private func notifyWebView(success: Bool, path: String) {
            let js = "window.dispatchEvent(new CustomEvent('nativeSaveResult', { detail: { success: \(success), path: '\(path.replacingOccurrences(of: "'", with: "\\'"))' } }));"
            DispatchQueue.main.async {
                self.webView?.evaluateJavaScript(js, completionHandler: nil)
            }
        }

        // MARK: - WKNavigationDelegate

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            updateStatus("Connected")
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            updateStatus("Load failed: \(error.localizedDescription)")
        }

        func webView(
            _ webView: WKWebView,
            didFailProvisionalNavigation navigation: WKNavigation!,
            withError error: Error
        ) {
            updateStatus("Cannot connect to \(appState.serverURL) - \(error.localizedDescription)")
        }

        // Trust self-signed / internal certificates
        func webView(
            _ webView: WKWebView,
            didReceive challenge: URLAuthenticationChallenge,
            completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
        ) {
            if challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
               let serverTrust = challenge.protectionSpace.serverTrust {
                completionHandler(.useCredential, URLCredential(trust: serverTrust))
            } else {
                completionHandler(.performDefaultHandling, nil)
            }
        }
    }
}
