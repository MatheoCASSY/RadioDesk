import { NextRequest, NextResponse } from 'next/server';

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || 'https://nu8n9r0hl5.execute-api.eu-west-1.amazonaws.com').replace(/\/+$/, '');

async function forward(request: NextRequest, method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE') {
  const suffix = request.nextUrl.pathname.replace(/^\/api\/musics/, '');
  const query = request.nextUrl.searchParams.toString();
  const url = `${API_BASE}/musics${suffix}${query ? `?${query}` : ''}`;

  const headers: Record<string, string> = {};
  const authHeader = request.headers.get('authorization');
  if (authHeader) headers.authorization = authHeader;

  let body: BodyInit | undefined;
  if (method === 'POST' || method === 'PUT' || method === 'PATCH') {
    const contentType = request.headers.get('content-type');
    if (contentType) headers['Content-Type'] = contentType;
    body = await request.arrayBuffer();
  }

  const res = await fetch(url, {
    method,
    headers,
    body,
  });

  const contentType = res.headers.get('content-type') || '';
  const isAudioLike = contentType.includes('audio/') || suffix.includes('/download');

  if (isAudioLike) {
    const data = await res.arrayBuffer();
    return new NextResponse(data, {
      status: res.status,
      headers: {
        'Content-Type': contentType || 'application/octet-stream',
        'Content-Disposition': res.headers.get('content-disposition') || '',
      },
    });
  }

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: {
      'Content-Type': contentType || 'application/json',
      'Next-Page': res.headers.get('Next-Page') || '',
      'Total-Page': res.headers.get('Total-Page') || '',
    },
  });
}

export async function GET(request: NextRequest) {
  try {
    return await forward(request, 'GET');
  } catch (error) {
    console.error('Proxy musics GET catch-all error:', error);
    return NextResponse.json({ error: 'Erreur du serveur proxy musics' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    return await forward(request, 'POST');
  } catch (error) {
    console.error('Proxy musics POST catch-all error:', error);
    return NextResponse.json({ error: 'Erreur du serveur proxy musics' }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    return await forward(request, 'PUT');
  } catch (error) {
    console.error('Proxy musics PUT catch-all error:', error);
    return NextResponse.json({ error: 'Erreur du serveur proxy musics' }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    return await forward(request, 'PATCH');
  } catch (error) {
    console.error('Proxy musics PATCH catch-all error:', error);
    return NextResponse.json({ error: 'Erreur du serveur proxy musics' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    return await forward(request, 'DELETE');
  } catch (error) {
    console.error('Proxy musics DELETE catch-all error:', error);
    return NextResponse.json({ error: 'Erreur du serveur proxy musics' }, { status: 500 });
  }
}
