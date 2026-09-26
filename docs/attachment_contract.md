# AI Coding Harness — Cross-Platform File Attachment & Upload Contract

## 1. Architectural Principles

The File Attachment & Upload system is designed to allow developers to supply contextual files—such as bug reports, runtime logs, dependency specifications, and issue descriptions—directly to the **AI Coding Harness**.

### The Unified Flow:
```
┌─────────────────────────────────┐   ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│           Web Client            │   │          macOS Client           │   │         Android Client          │
│   (Drag & Drop + File Picker)   │   │  (Native NSOpenPanel / Importer)│   │  (System Document File Picker)  │
└────────────────┬────────────────┘   └────────────────┬────────────────┘   └────────────────┬────────────────┘
                 │                                     │                                     │
                 └─────────────────────────────────────┼─────────────────────────────────────┘
                                                       ▼
                                            POST /api/v1/upload
                                        (multipart/form-data stream)
                                                       ▼
                                           ┌───────────────────────┐
                                           │  Harness Backend API  │
                                           └───────────┬───────────┘
                                                       ▼
                                           ┌───────────────────────┐
                                           │   Sandboxed Context   │
                                           │     & Tool Parser     │
                                           │ (FilesystemTool / AST)│
                                           └───────────────────────┘
```

### Critical Architectural Constraints:
1. **The browser must NOT directly manipulate arbitrary repository files**: Uploaded files are transmitted to the backend Harness. The backend validates, sandboxes, and stores or feeds the content into the orchestrator context.
2. **macOS Native File Selection**: The eventual Swift client uses native AppKit/SwiftUI file selection (`NSOpenPanel` or `.fileImporter(isPresented:allowedContentTypes:allowsMultipleSelection:)`) and posts the payload to the same `/upload` endpoint. Do NOT duplicate backend processing.
3. **Android Native File Selection**: The Android client uses the Android system document picker (`ActivityResultContracts.OpenDocument()` or `GetMultipleContents()`) and streams the selected file URIs to the same backend API.
4. **Single Backend Endpoint**: There is only one upload handling logic on the server (`POST /api/v1/upload`) shared uniformly across Web, macOS, and Android.

---

## 2. Shared Conceptual Model

The shared contract defines three core structures and a canonical `uploadFile()` API signature:

- **`Attachment`**: Complete metadata and state representation of an attached file.
- **`UploadRequest`**: Payload dispatched by clients to trigger an upload.
- **`UploadResult`**: Response returned upon completion or failure.

### Example Attachments:
- 📄 `error.log` (Tracebacks, stdout/stderr dumps)
- 📄 `requirements.txt` (Python package dependencies)
- 📄 `issue.md` (GitHub issue descriptions, reproduction steps)

---

### A. TypeScript Definitions (Web Client)

Defined in [`frontend/src/types/attachmentContract.ts`](file:///Users/arnavjindal2008/Desktop/AI%20Hack/iota-X/frontend/src/types/attachmentContract.ts):

```typescript
export type AttachmentStatus = 'uploading' | 'uploaded' | 'error';

export interface Attachment {
  id: string;
  name: string;
  size: number;
  type: string;
  status: AttachmentStatus;
  progress: number;
  error?: string;
  url?: string;
  content?: string;
  uploadedAt?: string;
}

export interface UploadRequest {
  file: File | Blob;
  filename: string;
  mimeType: string;
  size: number;
  conversationId?: string;
  onProgress?: (percent: number) => void;
}

export interface UploadResult {
  success: boolean;
  attachment: Attachment;
  error?: string;
}

export interface UploadApiService {
  uploadFile(request: UploadRequest): Promise<UploadResult>;
  deleteAttachment(attachmentId: string): Promise<boolean>;
}
```

---

### B. Swift Native Definitions (macOS Client)

```swift
import Foundation

// MARK: - 1. Attachment Status
public enum AttachmentStatus: String, Codable, Sendable {
    case uploading
    case uploaded
    case error
}

// MARK: - 2. Attachment
public struct Attachment: Codable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let size: Int
    public let type: String
    public var status: AttachmentStatus
    public var progress: Double
    public var error: String?
    public var url: String?
    public var content: String?
    public var uploadedAt: String?
}

// MARK: - 3. Upload Request
public struct UploadRequest: Sendable {
    public let fileURL: URL
    public let filename: String
    public let mimeType: String
    public let size: Int
    public let conversationId: String?
    public let onProgress: (@Sendable (Double) -> Void)?
}

// MARK: - 4. Upload Result
public struct UploadResult: Codable, Sendable {
    public let success: Bool
    public let attachment: Attachment
    public let error: String?
}

// MARK: - 5. Upload Client Protocol
public protocol UploadAPIClientProtocol: Sendable {
    func uploadFile(request: UploadRequest) async throws -> UploadResult
    func deleteAttachment(id: String) async throws -> Bool
}
```

#### macOS File Selection Implementation:
```swift
// Example SwiftUI .fileImporter invocation
.fileImporter(
    isPresented: $showFilePicker,
    allowedContentTypes: [.item],
    allowsMultipleSelection: true
) { result in
    switch result {
    case .success(let urls):
        for url in urls {
            guard url.startAccessingSecurityScopedResource() else { continue }
            defer { url.stopAccessingSecurityScopedResource() }
            Task {
                let req = UploadRequest(fileURL: url, filename: url.lastPathComponent, ...)
                _ = try await uploadClient.uploadFile(request: req)
            }
        }
    case .failure(let error):
        print("Picker error: \(error)")
    }
}
```

---

### C. Kotlin Native Definitions (Android Client)

```kotlin
package ai.codingharness.client.model.upload

import kotlinx.serialization.Serializable

// 1. Status
@Serializable
enum class AttachmentStatus {
    uploading, uploaded, error
}

// 2. Attachment
@Serializable
data class Attachment(
    val id: String,
    val name: String,
    val size: Long,
    val type: String,
    val status: AttachmentStatus = AttachmentStatus.uploading,
    val progress: Int = 0,
    val error: String? = null,
    val url: String? = null,
    val content: String? = null,
    val uploadedAt: String? = null
)

// 3. Upload Request
data class UploadRequest(
    val uri: android.net.Uri,
    val filename: String,
    val mimeType: String,
    val size: Long,
    val conversationId: String? = null,
    val onProgress: ((Int) -> Unit)? = null
)

// 4. Upload Result
@Serializable
data class UploadResult(
    val success: Boolean,
    val attachment: Attachment,
    val error: String? = null
)

// 5. Upload Repository Interface
interface UploadRepository {
    suspend fun uploadFile(request: UploadRequest): UploadResult
    suspend fun deleteAttachment(attachmentId: String): Boolean
}
```

#### Android System Document Picker Implementation:
```kotlin
// Example Jetpack Compose ActivityResult launcher
val launcher = rememberLauncherForActivityResult(
    contract = ActivityResultContracts.OpenMultipleDocuments()
) { uris: List<Uri> ->
    uris.forEach { uri ->
        val filename = context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            cursor.moveToFirst()
            cursor.getString(nameIndex)
        } ?: "attachment"
        
        viewModel.uploadAttachment(uri, filename)
    }
}
```

---

## 3. Web UI Capabilities Verified

1. **Drag & Drop**:
   - Dropping files onto the message composer highlights the zone with an animated dashed border and processes `dataTransfer.files`.
2. **File Picker**:
   - Paperclip button activates a hidden HTML file input with `multiple` enabled.
3. **Multiple Files**:
   - Simultaneous upload of multiple files (`error.log`, `requirements.txt`, `issue.md`).
4. **Upload Progress**:
   - Granular progress bar and percentage display per attachment chip.
5. **Metadata Display**:
   - Distinct icons based on file type (log: `text-rose-400`, code: `text-yellow-400`, json/toml: `text-amber-400`, markdown: `text-sky-400`).
   - Human-readable file size formatting (`KB`, `MB`).
6. **Remove & Cancel**:
   - `×` button allows immediate detachment and cleanup via `uploadApi.deleteAttachment()`.
7. **Upload Errors**:
   - Visual alert badges, red borders, and retry triggers for invalid or rejected files.
