import { GetObjectCommand, S3Client } from '@aws-sdk/client-s3';
import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

const BodySchema = z.object({
  bucket: z.string().min(1),
  key: z.string().min(1),
  credentials: z.object({
    AccessKeyId: z.string().min(1),
    SecretAccessKey: z.string().min(1),
    SessionToken: z.string().min(1),
  }),
  contentType: z.string().optional(),
  filename: z.string().optional(),
});

async function bodyToUint8Array(body: unknown): Promise<Uint8Array> {
  if (!body || typeof body !== 'object') {
    throw new Error('Réponse S3 invalide: body absent');
  }

  const candidate = body as {
    transformToByteArray?: () => Promise<Uint8Array>;
    arrayBuffer?: () => Promise<ArrayBuffer>;
  };

  if (typeof candidate.transformToByteArray === 'function') {
    return candidate.transformToByteArray();
  }

  if (typeof candidate.arrayBuffer === 'function') {
    return new Uint8Array(await candidate.arrayBuffer());
  }

  throw new Error('Body S3 non supporté');
}

export async function POST(request: NextRequest) {
  try {
    const raw = await request.json();
    const body = BodySchema.parse(raw);

    const s3Client = new S3Client({
      region: 'eu-west-1',
      credentials: {
        accessKeyId: body.credentials.AccessKeyId,
        secretAccessKey: body.credentials.SecretAccessKey,
        sessionToken: body.credentials.SessionToken,
      },
    });

    const result = await s3Client.send(new GetObjectCommand({
      Bucket: body.bucket,
      Key: body.key,
    }));

    const bytes = await bodyToUint8Array(result.Body);
    const normalizedBytes = new Uint8Array(bytes.byteLength);
    normalizedBytes.set(bytes);
    const contentType = result.ContentType || body.contentType || 'application/octet-stream';
    const filename = body.filename || body.key.split('/').pop() || 'music.bin';
    const payload = new Blob([normalizedBytes], { type: contentType });

    return new NextResponse(payload, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': `attachment; filename="${filename.replace(/"/g, '')}"`,
      },
    });
  } catch (error) {
    console.error('[api/s3-cache] GetObject failed', error);
    return NextResponse.json({ error: 'GetObject proxy failed' }, { status: 500 });
  }
}
