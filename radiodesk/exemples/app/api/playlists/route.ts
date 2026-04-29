import { NextRequest, NextResponse } from 'next/server';
import { PlaylistBase, FullPlaylist, PlaylistEditable } from '#/hen-types/playlist';
import { z } from 'zod';

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || 'https://nu8n9r0hl5.execute-api.eu-west-1.amazonaws.com').replace(/\/+$/, '');
const PLAYLIST_PATH_CANDIDATES = ['/playlists', '/playlist', '/admin/playlists'];

/**
 * Valide et parse la réponse JSON avec un schéma Zod
 */
async function validateJsonResponse<T>(response: Response, schema: z.ZodSchema<T>): Promise<T> {
  const text = await response.text();
  try {
    const data = JSON.parse(text);
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('Validation error:', error.issues);
      throw new Error(`Réponse API invalide: ${error.issues.map(e => `${e.path.join('.')}: ${e.message}`).join(', ')}`);
    }
    console.error('Parse error:', error);
    throw new Error(`Réponse API invalide: ${text.slice(0, 100)}`);
  }
}

async function forward(request: NextRequest, method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE', extraPath = '') {
  const query = request.nextUrl.searchParams.toString();
  const authHeader = request.headers.get('authorization');
  let body = method === 'POST' || method === 'PATCH' || method === 'PUT' ? await request.text() : undefined;

  // Valide le corps de la requête pour POST et PATCH
  if ((method === 'POST' || method === 'PATCH') && body) {
    try {
      const parsedBody = JSON.parse(body);
      PlaylistEditable.partial().parse(parsedBody);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return NextResponse.json({ error: 'Données invalides: ' + error.message }, { status: 400 });
      }
      return NextResponse.json({ error: 'Corps de requête invalide' }, { status: 400 });
    }
  }

  const headers: Record<string, string> = {};
  if (authHeader) headers.authorization = authHeader;
  if (method === 'POST' || method === 'PATCH' || method === 'PUT') {
    headers['Content-Type'] = request.headers.get('content-type') || 'application/json';
  }

  let lastRes: Response | null = null;
  for (const basePath of PLAYLIST_PATH_CANDIDATES) {
    const url = `${API_BASE}${basePath}${extraPath}${query ? `?${query}` : ''}`;
    const res = await fetch(url, { method, headers, body });
    if (res.status !== 404) {
      const text = await res.text();

      // Log structure for debugging - non-blocking validation
      if (res.ok && text && (method === 'GET' || method === 'POST' || method === 'PATCH')) {
        try {
          const data = JSON.parse(text);
          // Log if it's a list of playlists
          if (Array.isArray(data)) {
            console.log('[API playlists] Response is array with', data.length, 'items');
          }
          // Log if it's a single playlist
          else if (data.id && data.name) {
            console.log('[API playlists] Response is single playlist:', data.id);
          }
        } catch (error) {
          console.warn('[API playlists] Response parse warning:', error);
          // Continue anyway - don't block
        }
      }

      return new NextResponse(text, {
        status: res.status,
        headers: { 'Content-Type': res.headers.get('content-type') || 'application/json' },
      });
    }
    lastRes = res;
  }

  const fallbackText = lastRes ? await lastRes.text() : '{"message":"Not Found"}';
  return new NextResponse(fallbackText, {
    status: lastRes?.status || 404,
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function GET(request: NextRequest) {
  try {
    return await forward(request, 'GET');
  } catch (error) {
    console.error('Proxy playlists GET error:', error);
    return NextResponse.json({ error: 'Erreur du serveur proxy playlists' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    return await forward(request, 'POST');
  } catch (error) {
    console.error('Proxy playlists POST error:', error);
    return NextResponse.json({ error: 'Erreur du serveur proxy playlists' }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    return await forward(request, 'PUT');
  } catch (error) {
    console.error('Proxy playlists PUT error:', error);
    return NextResponse.json({ error: 'Erreur du serveur proxy playlists' }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    return await forward(request, 'PATCH');
  } catch (error) {
    console.error('Proxy playlists PATCH error:', error);
    return NextResponse.json({ error: 'Erreur du serveur proxy playlists' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    return await forward(request, 'DELETE');
  } catch (error) {
    console.error('Proxy playlists DELETE error:', error);
    return NextResponse.json({ error: 'Erreur du serveur proxy playlists' }, { status: 500 });
  }
}
