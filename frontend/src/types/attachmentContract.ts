/**
 * AI Coding Harness — Shared Cross-Platform File Attachment Contract
 *
 * Defines the core schemas for the File Attachment & Upload system across:
 * 1. Web / Desktop Web (React + TypeScript)
 * 2. macOS (Swift / SwiftUI via Codable)
 * 3. Android (Kotlin / Jetpack Compose via kotlinx.serialization)
 *
 * ARCHITECTURAL PRINCIPLES:
 * - The backend Harness is responsible for processing, indexing, and analyzing uploaded files.
 * - The browser must NOT directly manipulate arbitrary repository files.
 * - macOS uses native file selection APIs (NSOpenPanel / .fileImporter) and routes to the same backend.
 * - Android uses system document pickers (OpenDocument) and routes to the same backend.
 * - Single unified upload API endpoint across all platforms.
 */

// ============================================================================
// 1. Attachment Model
// ============================================================================

export type AttachmentStatus = 'uploading' | 'uploaded' | 'error';

export interface Attachment {
  /** Unique attachment identifier */
  id: string;
  /** Original filename (e.g. 'error.log', 'requirements.txt', 'issue.md') */
  name: string;
  /** Size in bytes */
  size: number;
  /** MIME type or file extension (e.g. 'text/plain', 'text/markdown') */
  type: string;
  /** Current upload status */
  status: AttachmentStatus;
  /** Upload completion percentage (0 - 100) */
  progress: number;
  /** Error message if status is 'error' */
  error?: string;
  /** Download / preview URL if persisted on server */
  url?: string;
  /** Text content for code, log, or markdown attachments */
  content?: string;
  /** ISO 8601 upload timestamp */
  uploadedAt?: string;
}

// ============================================================================
// 2. Upload Request
// ============================================================================

export interface UploadRequest {
  /** Raw file object, Blob, or base64 data */
  file: File | Blob;
  /** Filename */
  filename: string;
  /** MIME type */
  mimeType: string;
  /** Size in bytes */
  size: number;
  /** Associated conversation ID */
  conversationId?: string;
  /** Progress callback */
  onProgress?: (percent: number) => void;
}

// ============================================================================
// 3. Upload Result
// ============================================================================

export interface UploadResult {
  /** Whether the upload succeeded */
  success: boolean;
  /** Resulting attachment metadata */
  attachment: Attachment;
  /** Error details if upload failed */
  error?: string;
}
