/**
 * Upload API Service
 *
 * Implements the cross-platform file attachment/upload API contract.
 *
 * ARCHITECTURAL CONSTRAINTS:
 * - The browser must NOT directly manipulate arbitrary repository files.
 * - Files are dispatched to the Harness backend for sandboxed parsing and context extraction.
 * - Native macOS and Android clients will route through this same endpoint.
 */

import {
  Attachment,
  UploadRequest,
  UploadResult,
} from '../types/attachmentContract';

export interface UploadApiService {
  /** Upload a file with progress tracking and return an Attachment record */
  uploadFile(request: UploadRequest): Promise<UploadResult>;

  /** Delete or detach an uploaded file */
  deleteAttachment(attachmentId: string): Promise<boolean>;
}

// ============================================================================
// Concrete Implementation: MockUploadApiService
// Simulates network upload with progress reporting and validation.
// ============================================================================

export class MockUploadApiService implements UploadApiService {
  private attachments: Map<string, Attachment> = new Map();

  async uploadFile(request: UploadRequest): Promise<UploadResult> {
    const id = `att_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    const { filename, size, mimeType } = request;

    // Validation: enforce 25 MB limit
    const MAX_SIZE_BYTES = 25 * 1024 * 1024;
    if (size > MAX_SIZE_BYTES) {
      const error = `File size exceeds 25 MB limit (${(size / 1024 / 1024).toFixed(1)} MB)`;
      const failedAttachment: Attachment = {
        id,
        name: filename,
        size,
        type: mimeType || this.inferMimeType(filename),
        status: 'error',
        progress: 0,
        error,
      };
      return { success: false, attachment: failedAttachment, error };
    }

    // Simulate deliberate upload error test case
    if (filename.toLowerCase().includes('fail_upload')) {
      const error = 'Server rejected file upload: Invalid checksum';
      const failedAttachment: Attachment = {
        id,
        name: filename,
        size,
        type: mimeType || this.inferMimeType(filename),
        status: 'error',
        progress: 40,
        error,
      };
      return { success: false, attachment: failedAttachment, error };
    }

    // Simulate progressive network upload
    const progressSteps = [20, 50, 80, 100];
    for (const pct of progressSteps) {
      await new Promise((r) => setTimeout(r, 60));
      if (request.onProgress) {
        request.onProgress(pct);
      }
    }

    // Attempt to extract text preview for code/text files if File is readable
    let content: string | undefined = undefined;
    if (typeof window !== 'undefined' && request.file instanceof Blob) {
      try {
        if (size < 100 * 1024) {
          content = await request.file.text();
        }
      } catch {
        // Non-text file or read error
      }
    }

    const attachment: Attachment = {
      id,
      name: filename,
      size,
      type: mimeType || this.inferMimeType(filename),
      status: 'uploaded',
      progress: 100,
      content,
      uploadedAt: new Date().toISOString(),
    };

    this.attachments.set(id, attachment);

    return {
      success: true,
      attachment,
    };
  }

  async deleteAttachment(attachmentId: string): Promise<boolean> {
    return this.attachments.delete(attachmentId);
  }

  private inferMimeType(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'log':
        return 'text/x-log';
      case 'txt':
        return 'text/plain';
      case 'md':
        return 'text/markdown';
      case 'py':
        return 'text/x-python';
      case 'json':
        return 'application/json';
      case 'toml':
        return 'application/toml';
      case 'yaml':
      case 'yml':
        return 'application/yaml';
      case 'png':
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      default:
        return 'application/octet-stream';
    }
  }
}

export const uploadApi: UploadApiService = new MockUploadApiService();
