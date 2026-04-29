import { S3Client, UploadPartCommand } from '@aws-sdk/client-s3';
import { z } from 'zod';

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'https://nu8n9r0hl5.execute-api.eu-west-1.amazonaws.com').replace(/\/+$/, '');
const USE_PROXY = process.env.NEXT_PUBLIC_API_PROXY === '1';

function apiUrl(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return USE_PROXY ? `/api${normalizedPath}` : `${API_BASE}${normalizedPath}`;
}

const InitUploadResponseSchema = z.object({
  bucket: z.string(),
  key: z.string(),
  id: z.string(),
  uploadId: z.string(),
  credentials: z.object({
    AccessKeyId: z.string(),
    SecretAccessKey: z.string(),
    SessionToken: z.string(),
    Expiration: z.string(),
  }),
});

export type InitUploadResponse = z.infer<typeof InitUploadResponseSchema>;

export type MultipartUploadBody = Blob | ArrayBuffer | Uint8Array;

export async function initLargeUpload(mimeType: string, token?: string): Promise<InitUploadResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(apiUrl('/musics/init-upload'), {
    method: 'POST',
    headers,
    body: JSON.stringify({ mimetype: mimeType }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to init upload: ${res.status} ${errorText}`);
  }

  const data: unknown = await res.json();
  return InitUploadResponseSchema.parse(data);
}

export async function uploadPart(
  args: InitUploadResponse,
  body: MultipartUploadBody,
  partNumber = 1,
): Promise<{ ETag: string; PartNumber: number }> {
  const s3Client = new S3Client({
    region: 'eu-west-1',
    credentials: {
      accessKeyId: args.credentials.AccessKeyId,
      secretAccessKey: args.credentials.SecretAccessKey,
      sessionToken: args.credentials.SessionToken,
    },
  });

  // Force Uint8Array in browser to avoid SDK stream detection issues (e.g. getReader errors).
  const uploadBody = body instanceof Blob
    ? new Uint8Array(await body.arrayBuffer())
    : new Uint8Array(body);

  const command = new UploadPartCommand({
    Bucket: args.bucket,
    Key: args.key,
    UploadId: args.uploadId,
    PartNumber: partNumber,
    Body: uploadBody,
  });

  const res = await s3Client.send(command);
  if (!res.ETag) {
    throw new Error('ETag manquant dans la réponse S3');
  }

  return {
    ETag: res.ETag,
    PartNumber: partNumber,
  };
}

export async function completeLargeUpload(
  args: InitUploadResponse,
  parts: { ETag: string; PartNumber: number }[],
  token?: string,
): Promise<void> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(apiUrl('/musics/complete-upload'), {
    method: 'POST',
    headers,
    body: JSON.stringify({
      id: args.id,
      uploadId: args.uploadId,
      parts,
    }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to complete upload: ${res.status} ${errorText}`);
  }
}
