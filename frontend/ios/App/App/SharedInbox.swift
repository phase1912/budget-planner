import Foundation
import Capacitor

/// Hands the web layer what "Share → Budget Agent" left in the inbox it shares with the
/// share extension (F25.2.2). Each file is moved out to the app's own temporary folder as it
/// is taken, so a receipt is offered once, never on every start.
@objc(SharedInboxPlugin)
class SharedInboxPlugin: CAPPlugin, CAPBridgedPlugin {
    let identifier = "SharedInboxPlugin"
    let jsName = "SharedInbox"
    let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "take", returnType: CAPPluginReturnPromise)
    ]

    private static let inbox = FileManager.default
        .containerURL(forSecurityApplicationGroupIdentifier: "group.app.budgetagent")?
        .appendingPathComponent("SharedInbox", isDirectory: true)

    /// Resolves `{ files: [{ path, name }] }`, `path` being a URL the web view can fetch.
    @objc func take(_ call: CAPPluginCall) {
        let manager = FileManager.default
        guard let inbox = Self.inbox,
              let waiting = try? manager.contentsOfDirectory(at: inbox, includingPropertiesForKeys: nil)
        else { return call.resolve(["files": []]) }
        let taken = manager.temporaryDirectory.appendingPathComponent("Shared", isDirectory: true)
        try? manager.createDirectory(at: taken, withIntermediateDirectories: true)
        let files: [[String: String]] = waiting.sorted { $0.lastPathComponent < $1.lastPathComponent }.compactMap { file in
            let moved = taken.appendingPathComponent(file.lastPathComponent)
            guard (try? manager.moveItem(at: file, to: moved)) != nil,
                  let path = bridge?.portablePath(fromLocalURL: moved)?.absoluteString
            else { return nil }
            return ["path": path, "name": file.lastPathComponent]
        }
        call.resolve(["files": files])
    }
}
