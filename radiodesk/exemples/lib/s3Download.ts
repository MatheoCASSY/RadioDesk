import { GetObjectCommand, S3Client } from '@aws-sdk/client-s3';
import { z } from 'zod';

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'https://nu8n9r0hl5.execute-api.eu-west-1.amazonaws.com').replace(/\/+$/, '');
const USE_PROXY = process.env.NEXT_PUBLIC_API_PROXY !== '0';

function apiUrl(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return USE_PROXY ? `/api${normalizedPath}` : `${API_BASE}${normalizedPath}`;
}

function downloadInitEndpoints(id: string) {
  const path = `/musics/${encodeURIComponent(id)}?s3download=yes`;
  const proxy = `/api${path}`;
  const direct = `${API_BASE}${path}`;
  return [proxy, direct];
}

const DownloadInitResponseSchema = z.object({
  bucket: z.string(),
  key: z.string(),
  credentials: z.object({
    AccessKeyId: z.string(),
    SecretAccessKey: z.string(),
    SessionToken: z.string(),
  }),
  filename: z.string().optional(),
  contentType: z.string().optional(),
});

export type DownloadInitResponse = z.infer<typeof DownloadInitResponseSchema>;

export async function initS3Download(id: string, token?: string): Promise<DownloadInitResponse> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const endpoints = downloadInitEndpoints(id);
  let lastError: unknown = null;

  for (const endpoint of endpoints) {
    try {
      const res = await fetch(endpoint, {
        method: 'GET',
        headers,
      });

      if (!res.ok) {
        const errorText = await res.text();
        lastError = new Error(`Init download S3 échoué (${endpoint}): ${res.status} ${errorText}`);
        continue;
      }

      const payload: unknown = await res.json();
      return DownloadInitResponseSchema.parse(payload);
    } catch (error) {
      lastError = error;
    }
  }

  throw new Error(String((lastError as { message?: string })?.message ?? lastError ?? 'Init download S3 échoué'));
}

async function bodyToUint8Array(body: unknown): Promise<Uint8Array> {
  if (!body || typeof body !== 'object') {
    throw new Error('Réponse GetObject invalide: body absent');
  }

  const maybeBody = body as {
    transformToByteArray?: () => Promise<Uint8Array>;
    arrayBuffer?: () => Promise<ArrayBuffer>;
  };

  if (typeof maybeBody.transformToByteArray === 'function') {
    return maybeBody.transformToByteArray();
  }

  if (typeof maybeBody.arrayBuffer === 'function') {
    return new Uint8Array(await maybeBody.arrayBuffer());
  }

  throw new Error('Réponse GetObject non supportée dans ce runtime');
}

function filenameFromKey(key: string): string {
  const cleaned = key.split('?')[0];
  const parts = cleaned.split('/').filter(Boolean);
  return parts[parts.length - 1] || 'music.bin';
}

export async function getS3ObjectAsBlob(session: DownloadInitResponse): Promise<{ blob: Blob; filename: string }> {
  const filename = session.filename || filenameFromKey(session.key);

  // Prefer same-origin proxy to avoid browser CORS issues on S3 GET.
  try {
    const res = await fetch('/api/s3-cache', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/octet-stream',
      },
      body: JSON.stringify({
        bucket: session.bucket,
        key: session.key,
        credentials: session.credentials,
        contentType: session.contentType,
        filename,
      }),
    });

    if (res.ok) {
      const blob = await res.blob();
      return { blob, filename };
    }
  } catch {
    // Fallback to direct browser GetObject below.
  }

  const s3Client = new S3Client({
    region: 'eu-west-1',
    credentials: {
      accessKeyId: session.credentials.AccessKeyId,
      secretAccessKey: session.credentials.SecretAccessKey,
      sessionToken: session.credentials.SessionToken,
    },
  });

  const result = await s3Client.send(new GetObjectCommand({
    Bucket: session.bucket,
    Key: session.key,
  }));

  const bytes = await bodyToUint8Array(result.Body);
  const normalizedBytes = new Uint8Array(bytes.byteLength);
  normalizedBytes.set(bytes);
  const contentType = result.ContentType || session.contentType || 'application/octet-stream';

  return {
    blob: new Blob([normalizedBytes], { type: contentType }),
    filename,
  };
}