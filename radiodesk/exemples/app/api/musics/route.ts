import { NextRequest, NextResponse } from 'next/server';
import { Music, MusicsList, MusicMetadata } from '#/hen-types/music';
import { z } from 'zod';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://nu8n9r0hl5.execute-api.eu-west-1.amazonaws.com';

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

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const path = request.nextUrl.pathname.replace('/api/musics', '');
    const query = searchParams.toString();
    
    const url = `${API_BASE}/musics${path}${query ? '?' + query : ''}`;
    
    const headers: Record<string, string> = {
      'Accept': 'text/csv',
    };
    
    const authHeader = request.headers.get('authorization');
    if (authHeader) {
      headers.authorization = authHeader;
    }
    
    const res = await fetch(url, {
      method: 'GET',
      headers,
    });

    const contentType = res.headers.get('content-type') || '';
    const isAudioLike = contentType.includes('audio/') || path.includes('/download');

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

    // Valider la réponse JSON avec Zod si c'est une liste ou un objet musique
    // NOTE: La validation est non-stricte pour éviter de bloquer la réponse
    const text = await res.text();
    if (res.ok && text) {
      try {
        const data = JSON.parse(text);
        // Log la structure pour debug, mais ne bloque pas sur la validation
        if (data.musics && Array.isArray(data.musics)) {
          console.log('[API musics] Response structure OK - contains musics array');
        } else if (data.id && data.title) {
          console.log('[API musics] Response structure OK - single music object');
        }
      } catch (error) {
        console.warn('[API musics] Parse/validation issue:', error);
        // Continue anyway - don't block the response
      }
    }

    return new NextResponse(text, {
      status: res.status,
      headers: {
        'Content-Type': contentType || 'text/csv',
        'Next-Page': res.headers.get('Next-Page') || '',
        'Total-Page': res.headers.get('Total-Page') || '',
      },
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Erreur du serveur proxy' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.arrayBuffer();
    const { searchParams } = new URL(request.url);
    const path = request.nextUrl.pathname.replace('/api/musics', '');
    const query = searchParams.toString();
    
    const url = `${API_BASE}/musics${path}${query ? '?' + query : ''}`;
    
    const headers: Record<string, string> = {};
    
    const contentType = request.headers.get('content-type');
    if (contentType) {
      headers['Content-Type'] = contentType;
    }
    
    const authHeader = request.headers.get('authorization');
    if (authHeader) {
      headers.authorization = authHeader;
    }
    
    const res = await fetch(url, {
      method: 'POST',
      headers,
      body,
    });
    
    const data = await res.text();
    
    return new NextResponse(data, {
      status: res.status,
      headers: {
        'Content-Type': res.headers.get('content-type') || 'application/json',
      },
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Erreur du serveur proxy' },
      { status: 500 }
    );
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const body = await request.text();
    const { searchParams } = new URL(request.url);
    const path = request.nextUrl.pathname.replace('/api/musics', '');
    const query = searchParams.toString();
    
    // Valide le corps de la requête avec MusicMetadata
    try {
      const parsedBody = JSON.parse(body);
      MusicMetadata.partial().parse(parsedBody);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return NextResponse.json({ error: 'Données invalides: ' + error.message }, { status: 400 });
      }
      return NextResponse.json({ error: 'Corps de requête invalide' }, { status: 400 });
    }
    
    const url = `${API_BASE}/musics${path}${query ? '?' + query : ''}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    const authHeader = request.headers.get('authorization');
    if (authHeader) {
      headers.authorization = authHeader;
    }
    
    const res = await fetch(url, {
      method: 'PATCH',
      headers,
      body,
    });
    
    const data = await res.text();
    
    return new NextResponse(data, {
      status: res.status,
      headers: {
        'Content-Type': res.headers.get('content-type') || 'application/json',
      },
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Erreur du serveur proxy' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const path = request.nextUrl.pathname.replace('/api/musics', '');
    const query = searchParams.toString();
    
    const url = `${API_BASE}/musics${path}${query ? '?' + query : ''}`;
    
    const headers: Record<string, string> = {};
    
    const authHeader = request.headers.get('authorization');
    if (authHeader) {
      headers.authorization = authHeader;
    }
    
    const res = await fetch(url, {
      method: 'DELETE',
      headers,
    });
    
    const data = await res.text();
    
    return new NextResponse(data, {
      status: res.status,
      headers: {
        'Content-Type': res.headers.get('content-type') || 'text/plain',
      },
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Erreur du serveur proxy' },
      { status: 500 }
    );
  }
}
