'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useAuth } from 'react-oidc-context';
import DashboardShell from '@/components/admin/DashboardShell';
import { canAccessResource, filterMenuByAccess, firstAccessibleMenuHref } from '@/components/admin/menu';
import { Music, MusicsList } from '#/hen-types/music';
import { FullPlaylist, PlaylistBase } from '#/hen-types/playlist';

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

type RequestPreset = {
  id: string;
  label: string;
  method: HttpMethod;
  path: string;
  body?: string;
  includeAuth?: boolean;
};

type RequestResult = {
  requestId: string;
  label: string;
  method: HttpMethod;
  path: string;
  status: number;
  ok: boolean;
  durationMs: number;
  ranAt: string;
  requestBody?: string;
  responseBody: string;
  responseJson: unknown | null;
  parseError?: string;
  responseHeaders: Record<string, string>;
  henTypeChecks: HenTypeCheck[];
};

type HenTypeCheck = {
  schema: string;
  ok: boolean;
  issues?: string[];
};

function decodeJwtPayload(token?: string): Record<string, unknown> | null {
  if (!token) return null;
  const parts = token.split('.');
  if (parts.length < 2) return null;

  try {
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=');
    return JSON.parse(atob(padded)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function maybeParseJson(text: string): { json: unknown | null; parseError?: string } {
  if (!text.trim()) return { json: null };
  try {
    return { json: JSON.parse(text) as unknown };
  } catch (error) {
    return { json: null, parseError: String(error) };
  }
}

function issueList(issues: Array<{ path: PropertyKey[]; message: string }>): string[] {
  return issues.slice(0, 8).map((issue) => {
    const p = issue.path.length ? issue.path.map((key) => String(key)).join('.') : '(root)';
    return `${p}: ${issue.message}`;
  });
}

function unwrapObjectData(payload: unknown): unknown {
  if (!payload || typeof payload !== 'object') return payload;
  const obj = payload as Record<string, unknown>;
  if (obj.data && typeof obj.data === 'object') return obj.data;
  return payload;
}

function extractPlaylistArray(payload: unknown): unknown[] | null {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== 'object') return null;
  const obj = payload as Record<string, unknown>;
  if (Array.isArray(obj.data)) return obj.data as unknown[];
  if (Array.isArray(obj.playlists)) return obj.playlists as unknown[];
  return null;
}

function validateWithHenTypes(method: HttpMethod, path: string, payload: unknown | null): HenTypeCheck[] {
  if (!payload) return [];

  const checks: HenTypeCheck[] = [];
  const pathNoQuery = path.split('?')[0];

  if (method === 'GET' && pathNoQuery === '/api/musics' && path.includes('page=')) {
    const parsed = MusicsList.safeParse(payload);
    checks.push(parsed.success
      ? { schema: 'MusicsList', ok: true }
      : { schema: 'MusicsList', ok: false, issues: issueList(parsed.error.issues) });
  }

  if (/^\/api\/musics\/[^/]+$/.test(pathNoQuery) && (method === 'GET' || method === 'PATCH')) {
    const parsed = Music.safeParse(unwrapObjectData(payload));
    checks.push(parsed.success
      ? { schema: 'Music', ok: true }
      : { schema: 'Music', ok: false, issues: issueList(parsed.error.issues) });
  }

  if (pathNoQuery === '/api/playlists' && method === 'GET') {
    const list = extractPlaylistArray(payload);
    if (!list) {
      checks.push({ schema: 'PlaylistBase[]', ok: false, issues: ['(root): tableau introuvable (attendu array/data/playlists)'] });
    } else {
      const issues: string[] = [];
      for (let i = 0; i < list.length; i++) {
        const parsed = PlaylistBase.safeParse(list[i]);
        if (!parsed.success) {
          const itemIssues = issueList(parsed.error.issues).map((e) => `[${i}] ${e}`);
          issues.push(...itemIssues);
          if (issues.length >= 8) break;
        }
      }
      checks.push(issues.length === 0
        ? { schema: 'PlaylistBase[]', ok: true }
        : { schema: 'PlaylistBase[]', ok: false, issues: issues.slice(0, 8) });
    }
  }

  if (/^\/api\/playlists\/[^/]+$/.test(pathNoQuery) && (method === 'GET' || method === 'PATCH' || method === 'PUT' || method === 'POST')) {
    const parsed = FullPlaylist.safeParse(unwrapObjectData(payload));
    checks.push(parsed.success
      ? { schema: 'FullPlaylist', ok: true }
      : { schema: 'FullPlaylist', ok: false, issues: issueList(parsed.error.issues) });
  }

  return checks;
}

export default function DebugApiPage() {
  const auth = useAuth();
  const [playlistId, setPlaylistId] = useState('');
  const [musicId, setMusicId] = useState('');

  const [customMethod, setCustomMethod] = useState<HttpMethod>('GET');
  const [customPath, setCustomPath] = useState('/api/playlists');
  const [customBody, setCustomBody] = useState('');
  const [customUseAuth, setCustomUseAuth] = useState(true);

  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<RequestResult[]>([]);

  const token = auth.user?.access_token;
  const userEmail = auth.user?.profile?.email || auth.user?.profile?.preferred_username || 'debug-user';
  const tokenPayload = useMemo(() => decodeJwtPayload(token), [token]);

  const presets = useMemo<RequestPreset[]>(() => {
    const selectedPlaylistId = playlistId.trim() || 'playlist-id';
    const selectedMusicId = musicId.trim() || 'music-id';

    return [
      { id: 'get-playlists', label: 'GET playlists', method: 'GET', path: '/api/playlists' },
      { id: 'get-playlist-by-id', label: 'GET playlist by id', method: 'GET', path: `/api/playlists/${selectedPlaylistId}` },
      { id: 'get-playlist-subpath', label: 'GET playlist nested path', method: 'GET', path: `/api/playlists/${selectedPlaylistId}/tracks` },
      { id: 'get-musics-page-0', label: 'GET musics page 0', method: 'GET', path: '/api/musics?page=0' },
      { id: 'get-musics-page-1', label: 'GET musics page 1', method: 'GET', path: '/api/musics?page=1' },
      { id: 'get-music-by-id', label: 'GET music by id', method: 'GET', path: `/api/musics/${selectedMusicId}` },
      { id: 'get-music-download', label: 'GET music s3download init', method: 'GET', path: `/api/musics/${selectedMusicId}?s3download=yes` },
      { id: 'get-streaming-status', label: 'GET streaming status', method: 'GET', path: '/api/streaming/status', includeAuth: false },
      { id: 'get-admin-cache', label: 'GET admin cache page 0', method: 'GET', path: '/api/admin/cache?page=0' },
      { id: 'get-admin-cache-page-1', label: 'GET admin cache page 1', method: 'GET', path: '/api/admin/cache?page=1' },
      { id: 'get-s3-cache', label: 'GET s3-cache', method: 'GET', path: '/api/s3-cache', includeAuth: false },
      {
        id: 'post-playlists',
        label: 'POST create playlist',
        method: 'POST',
        path: '/api/playlists',
        body: JSON.stringify({ name: `debug-${Date.now()}`, author: userEmail }, null, 2),
      },
      {
        id: 'patch-playlist-by-id',
        label: 'PATCH playlist by id',
        method: 'PATCH',
        path: `/api/playlists/${selectedPlaylistId}`,
        body: JSON.stringify({ name: 'Debug playlist', author: userEmail, musics: [selectedMusicId] }, null, 2),
      },
      {
        id: 'patch-music-by-id',
        label: 'PATCH music metadata by id',
        method: 'PATCH',
        path: `/api/musics/${selectedMusicId}`,
        body: JSON.stringify({ title: 'Debug title', artist: 'Debug artist', album: 'Debug album', year: '2026' }, null, 2),
      },
      {
        id: 'delete-playlist-by-id',
        label: 'DELETE playlist by id',
        method: 'DELETE',
        path: `/api/playlists/${selectedPlaylistId}`,
      },
      {
        id: 'delete-music-by-id-path',
        label: 'DELETE music by id (path)',
        method: 'DELETE',
        path: `/api/musics/${selectedMusicId}`,
      },
      {
        id: 'delete-music-by-id-query',
        label: 'DELETE music by id (query)',
        method: 'DELETE',
        path: `/api/musics?id=${selectedMusicId}`,
      },
      {
        id: 'delete-music-by-id-body',
        label: 'DELETE music by id (body)',
        method: 'DELETE',
        path: '/api/musics',
        body: JSON.stringify({ id: selectedMusicId }, null, 2),
      },
      {
        id: 'post-stream-control-start',
        label: 'POST streaming control start',
        method: 'POST',
        path: '/api/streaming/control',
        body: JSON.stringify({ action: 'start' }, null, 2),
        includeAuth: false,
      },
      {
        id: 'post-stream-control-skip',
        label: 'POST streaming control skip',
        method: 'POST',
        path: '/api/streaming/control',
        body: JSON.stringify({ action: 'skip' }, null, 2),
        includeAuth: false,
      },
      {
        id: 'post-stream-control-stop',
        label: 'POST streaming control stop',
        method: 'POST',
        path: '/api/streaming/control',
        body: JSON.stringify({ action: 'stop' }, null, 2),
        includeAuth: false,
      },
      {
        id: 'post-stream-control-reload',
        label: 'POST streaming control reload',
        method: 'POST',
        path: '/api/streaming/control',
        body: JSON.stringify({ action: 'reload' }, null, 2),
        includeAuth: false,
      },
    ];
  }, [musicId, playlistId, userEmail]);

  const runRequest = async (preset: RequestPreset) => {
    setRunning(preset.id);

    const startedAt = performance.now();
    const headers: Record<string, string> = {};
    if (preset.includeAuth !== false && token) headers.Authorization = `Bearer ${token}`;

    const body = preset.body?.trim() ? preset.body : undefined;
    if (body) headers['Content-Type'] = 'application/json';

    try {
      const response = await fetch(preset.path, {
        method: preset.method,
        headers,
        body,
        cache: 'no-store',
      });

      const responseBody = await response.text();
      const parsed = maybeParseJson(responseBody);
      const henTypeChecks = validateWithHenTypes(preset.method, preset.path, parsed.json);
      const responseHeaders: Record<string, string> = {};
      response.headers.forEach((value, key) => {
        responseHeaders[key] = value;
      });

      const item: RequestResult = {
        requestId: `${preset.id}-${Date.now()}`,
        label: preset.label,
        method: preset.method,
        path: preset.path,
        status: response.status,
        ok: response.ok,
        durationMs: Math.round(performance.now() - startedAt),
        ranAt: new Date().toISOString(),
        requestBody: body,
        responseBody,
        responseJson: parsed.json,
        parseError: parsed.parseError,
        responseHeaders,
        henTypeChecks,
      };

      setResults((prev) => [item, ...prev]);
    } catch (error) {
      const item: RequestResult = {
        requestId: `${preset.id}-${Date.now()}`,
        label: preset.label,
        method: preset.method,
        path: preset.path,
        status: 0,
        ok: false,
        durationMs: Math.round(performance.now() - startedAt),
        ranAt: new Date().toISOString(),
        requestBody: body,
        responseBody: '',
        responseJson: null,
        parseError: String(error),
        responseHeaders: {},
        henTypeChecks: [],
      };
      setResults((prev) => [item, ...prev]);
    } finally {
      setRunning(null);
    }
  };

  const runSafeGetRequests = async () => {
    const safe = presets.filter((preset) => preset.method === 'GET');
    for (const preset of safe) {
      await runRequest(preset);
    }
  };

  const runAllPresets = async () => {
    if (!window.confirm('Exécuter tous les presets, y compris POST/PATCH/DELETE ?')) return;
    for (const preset of presets) {
      await runRequest(preset);
    }
  };

  const runCustomRequest = async () => {
    const id = `custom-${Date.now()}`;
    await runRequest({
      id,
      label: 'Custom request',
      method: customMethod,
      path: customPath,
      body: customBody,
      includeAuth: customUseAuth,
    });
  };

  const signOutRedirect = () => {
    try {
      const maybeSignout = auth as unknown as { signoutRedirect?: () => Promise<void> | void };
      if (typeof maybeSignout.signoutRedirect === 'function') {
        void maybeSignout.signoutRedirect();
        return;
      }
    } catch {}
    auth.removeUser();
  };

  if (auth.isLoading) return <div className="min-h-screen flex items-center justify-center">Chargement...</div>;
  if (auth.error) return <div className="min-h-screen flex items-center justify-center">Erreur d&apos;authentification</div>;

  if (!auth.isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-4">Vous n&apos;êtes pas connecté</h2>
          <button onClick={() => auth.signinRedirect()} className="rounded-full bg-zinc-900 text-white px-6 py-2">Se connecter</button>
        </div>
      </div>
    );
  }

  const profile = (auth.user?.profile ?? null) as Record<string, unknown> | null;
  const visibleMenu = filterMenuByAccess(profile);
  const fallbackHref = firstAccessibleMenuHref(profile);
  const authorized = canAccessResource('debug-api', profile);

  if (!authorized) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center max-w-xl">
          <h2 className="text-2xl font-semibold mb-4">Accès refusé</h2>
          <p className="mb-6 text-zinc-600">Votre groupe IAM ne permet pas d&apos;accéder à cette page.</p>
          <Link href={fallbackHref} className="rounded-full bg-zinc-900 text-white px-6 py-2 inline-block">Retour au dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <DashboardShell
      visibleMenu={visibleMenu}
      activeSlug="debug-api"
      topbarTag="FluffRadio - Debug API"
      liveTitle="Debug API"
      pageTitle="Debug API"
      userLabel={auth.user?.profile?.name ?? auth.user?.profile?.email ?? 'Admin'}
      onLogout={signOutRedirect}
      breadcrumbs={<><span>Accueil</span><span>/</span><span className="active">Debug API</span></>}
    >
      <section className="fluff-table-panel" style={{ padding: '1rem' }}>
        <h2 style={{ marginTop: 0 }}>Contexte Auth & Token</h2>
        <div style={{ display: 'grid', gap: '0.7rem', gridTemplateColumns: '1fr 1fr' }}>
          <div>
            <div style={{ fontSize: '0.85rem', color: '#666' }}>Authentifié</div>
            <strong>{String(auth.isAuthenticated)}</strong>
          </div>
          <div>
            <div style={{ fontSize: '0.85rem', color: '#666' }}>Longueur token</div>
            <strong>{token?.length ?? 0}</strong>
          </div>
        </div>

        <div style={{ marginTop: '0.8rem' }}>
          <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.25rem' }}>Payload JWT décodé</div>
          <pre style={{ background: '#111', color: '#39d98a', padding: '0.75rem', borderRadius: 8, overflow: 'auto' }}>
            {JSON.stringify(tokenPayload, null, 2)}
          </pre>
        </div>

        <div style={{ marginTop: '0.8rem' }}>
          <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.25rem' }}>Profil user OIDC</div>
          <pre style={{ background: '#111', color: '#f7f7f7', padding: '0.75rem', borderRadius: 8, overflow: 'auto' }}>
            {JSON.stringify(auth.user?.profile ?? null, null, 2)}
          </pre>
        </div>
      </section>

      <section className="fluff-table-panel" style={{ padding: '1rem' }}>
        <h2 style={{ marginTop: 0 }}>Presets de debug</h2>
        <p style={{ margin: '0 0 0.8rem', color: '#666' }}>
          Renseigne un ID playlist / musique existant pour tester GET/PATCH/DELETE ciblés.
        </p>

        <div style={{ display: 'grid', gap: '0.7rem', gridTemplateColumns: '1fr 1fr' }}>
          <input
            value={playlistId}
            onChange={(e) => setPlaylistId(e.target.value)}
            className="fluff-input"
            placeholder="playlistId (ex: e1rqct...)"
          />
          <input
            value={musicId}
            onChange={(e) => setMusicId(e.target.value)}
            className="fluff-input"
            placeholder="musicId (ex: 1234...)"
          />
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.8rem', flexWrap: 'wrap' }}>
          <button className="fluff-btn-primary" onClick={runSafeGetRequests} disabled={running !== null}>
            {running ? 'Exécution...' : 'Lancer tous les GET'}
          </button>
          <button className="fluff-btn-secondary" onClick={runAllPresets} disabled={running !== null}>
            {running ? 'Exécution...' : 'Lancer tous les presets'}
          </button>
          <button className="fluff-btn-secondary" onClick={() => setResults([])}>
            Vider les sorties
          </button>
        </div>

        <div style={{ marginTop: '1rem', display: 'grid', gap: '0.6rem' }}>
          {presets.map((preset) => (
            <div key={preset.id} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '0.7rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.7rem' }}>
                <div>
                  <strong>{preset.label}</strong>
                  <div style={{ fontSize: '0.85rem', color: '#666' }}>{preset.method} {preset.path}</div>
                </div>
                <button
                  className="fluff-btn-secondary"
                  onClick={() => runRequest(preset)}
                  disabled={running !== null}
                >
                  Exécuter
                </button>
              </div>
              {preset.body && (
                <pre style={{ marginTop: '0.6rem', background: '#f8fafc', padding: '0.6rem', borderRadius: 6, overflow: 'auto' }}>
                  {preset.body}
                </pre>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="fluff-table-panel" style={{ padding: '1rem' }}>
        <h2 style={{ marginTop: 0 }}>Requête custom</h2>
        <div style={{ display: 'grid', gap: '0.7rem', gridTemplateColumns: '140px 1fr' }}>
          <select className="fluff-input" value={customMethod} onChange={(e) => setCustomMethod(e.target.value as HttpMethod)}>
            <option>GET</option>
            <option>POST</option>
            <option>PATCH</option>
            <option>PUT</option>
            <option>DELETE</option>
          </select>
          <input
            value={customPath}
            onChange={(e) => setCustomPath(e.target.value)}
            className="fluff-input"
            placeholder="/api/playlists"
          />
        </div>

        <textarea
          value={customBody}
          onChange={(e) => setCustomBody(e.target.value)}
          className="fluff-input"
          placeholder="Body JSON (facultatif)"
          style={{ marginTop: '0.7rem', minHeight: 130 }}
        />

        <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.7rem' }}>
          <input type="checkbox" checked={customUseAuth} onChange={(e) => setCustomUseAuth(e.target.checked)} />
          Envoyer le token Authorization
        </label>

        <div style={{ marginTop: '0.7rem' }}>
          <button className="fluff-btn-primary" onClick={runCustomRequest} disabled={running !== null || !customPath.trim()}>
            Exécuter la requête custom
          </button>
        </div>
      </section>

      <section className="fluff-table-panel" style={{ padding: '1rem' }}>
        <h2 style={{ marginTop: 0 }}>Sorties des requêtes</h2>
        {results.length === 0 ? (
          <div className="fluff-empty-state">Aucune sortie pour le moment</div>
        ) : (
          <div style={{ display: 'grid', gap: '0.8rem' }}>
            {results.map((result) => (
              <article key={result.requestId} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '0.8rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem' }}>
                  <strong>{result.label}</strong>
                  <span style={{ color: result.ok ? '#059669' : '#dc2626' }}>
                    HTTP {result.status} • {result.durationMs}ms
                  </span>
                </div>
                <div style={{ fontSize: '0.86rem', color: '#666', marginTop: '0.2rem' }}>
                  {result.method} {result.path} • {result.ranAt}
                </div>

                {result.requestBody && (
                  <>
                    <div style={{ marginTop: '0.65rem', fontSize: '0.85rem', color: '#666' }}>Body envoyé</div>
                    <pre style={{ background: '#f8fafc', padding: '0.65rem', borderRadius: 6, overflow: 'auto' }}>{result.requestBody}</pre>
                  </>
                )}

                {result.henTypeChecks.length > 0 && (
                  <>
                    <div style={{ marginTop: '0.65rem', fontSize: '0.85rem', color: '#666' }}>Validation hen-types</div>
                    <div style={{ display: 'grid', gap: '0.45rem' }}>
                      {result.henTypeChecks.map((check, idx) => (
                        <div key={`${result.requestId}-check-${idx}`} style={{ border: '1px solid #e5e7eb', borderRadius: 6, padding: '0.55rem', background: '#fff' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
                            <strong>{check.schema}</strong>
                            <span style={{ color: check.ok ? '#059669' : '#dc2626' }}>{check.ok ? 'OK' : 'KO'}</span>
                          </div>
                          {!check.ok && check.issues && check.issues.length > 0 && (
                            <pre style={{ marginTop: '0.45rem', background: '#f8fafc', padding: '0.55rem', borderRadius: 6, overflow: 'auto' }}>
                              {check.issues.join('\n')}
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}

                <div style={{ marginTop: '0.65rem', fontSize: '0.85rem', color: '#666' }}>Headers réponse</div>
                <pre style={{ background: '#f8fafc', padding: '0.65rem', borderRadius: 6, overflow: 'auto' }}>
                  {JSON.stringify(result.responseHeaders, null, 2)}
                </pre>

                <div style={{ marginTop: '0.65rem', fontSize: '0.85rem', color: '#666' }}>JSON parsé</div>
                <pre style={{ background: '#111', color: '#39d98a', padding: '0.65rem', borderRadius: 6, overflow: 'auto' }}>
                  {JSON.stringify(result.responseJson, null, 2)}
                </pre>

                <div style={{ marginTop: '0.65rem', fontSize: '0.85rem', color: '#666' }}>Body brut</div>
                <pre style={{ background: '#f1f5f9', padding: '0.65rem', borderRadius: 6, overflow: 'auto' }}>
                  {result.responseBody || '(vide)'}
                </pre>

                {result.parseError && (
                  <div style={{ marginTop: '0.55rem', color: '#dc2626', fontSize: '0.85rem' }}>
                    Parse JSON: {result.parseError}
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </DashboardShell>
  );
}
