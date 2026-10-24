import UIKit
import UniformTypeIdentifiers

/// "Share → Budget Agent" from Photos, Files or Mail (F25.2.2): the receipt photos and PDFs
/// shared are copied into the inbox the app shares with this extension, and the app opens
/// them on the add-a-receipt screen the next time it comes to the front. Nothing is sent
/// anywhere from here, and nothing but images and PDFs is taken.
class ShareViewController: UIViewController {
    /// The folder both the app and this extension can reach; the app empties it.
    static let inbox = FileManager.default
        .containerURL(forSecurityApplicationGroupIdentifier: "group.app.budgetagent")?
        .appendingPathComponent("SharedInbox", isDirectory: true)

    /// The same limit as a receipt's photos on the upload screen.
    private let most = 10
    private let message = UILabel()
    private let done = UIButton(type: .system)

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        message.numberOfLines = 0
        message.textAlignment = .center
        message.font = .preferredFont(forTextStyle: .headline)
        message.text = NSLocalizedString("saving", comment: "While the shared files are copied")
        done.setTitle(NSLocalizedString("done", comment: "Closes the share sheet"), for: .normal)
        done.titleLabel?.font = .preferredFont(forTextStyle: .headline)
        done.isHidden = true
        done.addTarget(self, action: #selector(close), for: .touchUpInside)
        let stack = UIStackView(arrangedSubviews: [message, done])
        stack.axis = .vertical
        stack.spacing = 20
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            stack.leadingAnchor.constraint(equalTo: view.layoutMarginsGuide.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: view.layoutMarginsGuide.trailingAnchor),
            done.heightAnchor.constraint(greaterThanOrEqualToConstant: 44),
        ])
        Task { await keep() }
    }

    /// Copies every shared image or PDF into the inbox and says how it went.
    private func keep() async {
        let attachments = (extensionContext?.inputItems as? [NSExtensionItem] ?? [])
            .flatMap { $0.attachments ?? [] }
        // Named by when and in which order they came, so a long receipt's parts stay in order.
        let batch = Int(Date().timeIntervalSince1970 * 1000)
        var kept = 0
        for attachment in attachments where kept < most {
            if await copy(attachment, as: String(format: "%ld-%02ld", batch, kept)) { kept += 1 }
        }
        message.text = kept > 0
            ? NSLocalizedString("kept", comment: "The files wait in the app")
            : NSLocalizedString("nothing", comment: "Nothing shared was a photo or a PDF")
        done.isHidden = false
    }

    private func copy(_ attachment: NSItemProvider, as stem: String) async -> Bool {
        let type = [UTType.pdf, UTType.image].first { attachment.hasItemConformingToTypeIdentifier($0.identifier) }
        guard let type, let inbox = Self.inbox else { return false }
        return await withCheckedContinuation { done in
            // The system's copy lives only inside this callback, so it is moved out here.
            _ = attachment.loadFileRepresentation(forTypeIdentifier: type.identifier) { url, _ in
                guard let url else { return done.resume(returning: false) }
                let name = "\(stem).\(url.pathExtension.isEmpty ? "jpg" : url.pathExtension)"
                do {
                    try FileManager.default.createDirectory(at: inbox, withIntermediateDirectories: true)
                    try FileManager.default.copyItem(at: url, to: inbox.appendingPathComponent(name))
                    done.resume(returning: true)
                } catch {
                    done.resume(returning: false)
                }
            }
        }
    }

    @objc private func close() {
        extensionContext?.completeRequest(returningItems: nil)
    }
}
