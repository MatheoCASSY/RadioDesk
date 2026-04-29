'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { formatDuration } from '@/lib/formatDuration';
import ListPaginationControls, { type PageSize } from './ListPaginationControls';

interface Music {
  id: string;
  title: string;
  artist: string;
  duration: string;
  tags?: string[];
}

interface Playlist {
  id: string;
  name: string;
  author?: string;
  description?: string;
  musics?: unknown[];
  musicIds?: unknown[];
  ids?: unknown[];
}

interface PlaylistManagerProps {
  apiBaseUrl: string;
  token?: string;
  userEmail?: string;
}

type PlaylistListResponse = {
  data?: Playlist[];
  playlists?: Playlist[];
  metadata?: { total?: number };
};

function normalizePlaylistsResponse(payload: unknown): Playlist[] {
  if (Array.isArray(payload)) return payload as Playlist[];
  if (!payload || typeof payload !== 'object') return [];

  const obj = payload as Record<string, unknown>;
  if (Array.isArray(obj.data)) return obj.data as Playlist[];
  if (Array.isArray(obj.playlists)) return obj.playlists as Playlist[];
  return [];
}

function normalizePlaylistTracks(payload: unknown): Music[] {
  if (!Array.isArray(payload)) return [];

  return payload
    .map((item) => {
      if (typeof item === 'string') {
        return { id: item, title: item, artist: '', duration: '' } as Music;
      }
      if (item && typeof item === 'object') {
        const row = item as Record<string, unknown>;
        const id = typeof row.id === 'string' ? row.id : '';
        if (!id) return null;
        return {
          id,
          title: typeof row.title === 'string' ? row.title : id,
          artist: typeof row.artist === 'string' ? row.artist : '',
          duration: typeof row.duration === 'string' ? row.duration : '',
          tags: Array.isArray(row.tags) ? (row.tags as string[]) : [],
        } as Music;
      }
      return null;
    })
    .filter((item): item is Music => item !== null);
}

function countPlaylistTrackIds(playlist: Playlist): number {
  const candidates = [playlist.musics, playlist.musicIds, playlist.ids].find(Array.isArray) ?? [];

  return candidates.reduce((count, item) => {
    if (typeof item === 'string') return item.trim() ? count + 1 : count;
    if (item && typeof item === 'object') {
      const id = (item as { id?: unknown }).id;
      return typeof id === 'string' && id.trim() ? count + 1 : count;
    }
    return count;
  }, 0);
}

function extractTrackCountFromPayload(payload: unknown): number {
  if (!payload || typeof payload !== 'object') return 0;

  const obj = payload as Record<string, unknown>;
  const candidates = [obj.musics, obj.musicIds, obj.ids].find(Array.isArray) ?? [];

  return candidates.reduce((count, item) => {
    if (typeof item === 'string') return item.trim() ? count + 1 : count;
    if (item && typeof item === 'object') {
      const id = (item as { id?: unknown }).id;
      return typeof id === 'string' && id.trim() ? count + 1 : count;
    }
    return count;
  }, 0);
}

// Helper function to build API URLs with proxy support
function buildApiUrl(baseUrl: string, path: string): string {
  void baseUrl;
  // Always use same-origin proxy for playlist manager requests.
  return `/api${path}`;
}

function extractAuthorFromToken(token?: string): string | null {
  if (!token) return null;
  const tokenParts = token.split('.');
  if (tokenParts.length < 2) return null;

  try {
    const base64 = tokenParts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=');
    const payload = JSON.parse(atob(padded));
    return payload.email || payload['cognito:username'] || payload.preferred_username || payload.username || payload.sub || null;
  } catch {
    return null;
  }
}

export default function PlaylistManager({ apiBaseUrl, token, userEmail }: PlaylistManagerProps) {
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [selectedPlaylist, setSelectedPlaylist] = useState<Playlist | null>(null);
  const [availableMusics, setAvailableMusics] = useState<Music[]>([]);
  const [selectedMusicIds, setSelectedMusicIds] = useState<Set<string>>(new Set());
  const [playlistTracks, setPlaylistTracks] = useState<Music[]>([]);
  const [playlistTrackCounts, setPlaylistTrackCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draggedTrackIndex, setDraggedTrackIndex] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'tracks' | 'albums' | 'artists' | 'folders'>('tracks');
  const [searchQuery, setSearchQuery] = useState('');
  const [availableMusicPageSize, setAvailableMusicPageSize] = useState<PageSize>(25);
  const [availableMusicPage, setAvailableMusicPage] = useState(0);
  const [playlistTrackPageSize, setPlaylistTrackPageSize] = useState<PageSize>(25);
  const [playlistTrackPage, setPlaylistTrackPage] = useState(0);
  const [isCreating, setIsCreating] = useState(false);
  const [newPlaylistName, setNewPlaylistName] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Fetch playlists (GET /playlists)
  const fetchPlaylists = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const headers: Record<string, string> = {};
      if (token) headers.Authorization = `Bearer ${token}`;
      
      const url = buildApiUrl(apiBaseUrl, '/playlists');
      console.log('📡 Fetching playlists from:', url);
      
      const res = await fetch(url, { headers });
      if (res.ok) {
        const data = await res.json() as Playlist[] | PlaylistListResponse;
        const normalized = normalizePlaylistsResponse(data);
        console.log('📦 Raw playlists data:', data);
        console.log('✅ Normalized playlists:', normalized);
        setPlaylists(normalized);

        // If list endpoint omits track IDs, hydrate counts from details endpoint in background.
        const missingCountPlaylists = normalized.filter((pl) => countPlaylistTrackIds(pl) === 0);
        if (missingCountPlaylists.length > 0) {
          Promise.all(
            missingCountPlaylists.map(async (pl) => {
              try {
                const detailRes = await fetch(buildApiUrl(apiBaseUrl, `/playlists/${pl.id}`), { headers });
                if (!detailRes.ok) return { id: pl.id, count: 0 };
                const detailData = await detailRes.json() as { data?: unknown } | unknown;
                const payload = detailData && typeof detailData === 'object' && 'data' in (detailData as Record<string, unknown>)
                  ? (detailData as { data?: unknown }).data
                  : detailData;
                return { id: pl.id, count: extractTrackCountFromPayload(payload) };
              } catch {
                return { id: pl.id, count: 0 };
              }
            })
          ).then((entries) => {
            setPlaylistTrackCounts((prev) => {
              const next = { ...prev };
              for (const entry of entries) {
                next[entry.id] = entry.count;
              }
              return next;
            });
          });
        }
      } else {
        const errorText = await res.text();
        if (res.status === 404) {
          setError('Route playlists indisponible sur le backend (404).');
        } else {
          setError(`Erreur ${res.status}: ${res.statusText}`);
        }
        console.error('API playlists error:', errorText.slice(0, 300));
      }
    } catch (error) {
      console.error('Erreur lors du chargement des playlists:', error);
      const errorMsg = error instanceof Error ? error.message : 'Erreur de connexion';
      setError(`❌ ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, token]);

  // Fetch available musics from /musics endpoint
  const fetchAvailableMusics = useCallback(async () => {
    try {
      const headers: Record<string, string> = { Accept: 'application/json, text/csv;q=0.9' };
      if (token) headers.Authorization = `Bearer ${token}`;

      const byId = new Map<string, Music>();
      const visitedPages = new Set<number>();
      let nextPage: number | null = 0;
      let headerTotalPages: number | null = null;

      while (nextPage !== null && visitedPages.size < 500) {
        const page: number = nextPage;
        if (visitedPages.has(page)) break;
        visitedPages.add(page);

        const res = await fetch(buildApiUrl(apiBaseUrl, `/musics?page=${page}`), { headers, cache: 'no-store' });
        if (!res.ok) {
          const errText = await res.text().catch(() => '');
          console.error('Erreur API musics:', res.status, res.statusText, errText.slice(0, 300));
          break;
        }

        const contentType = res.headers.get('content-type') || '';
        const text = await res.text();
        let pageMusics: Music[] = [];

        if (contentType.includes('application/json') || text.trim().startsWith('{') || text.trim().startsWith('[')) {
          try {
            const data = JSON.parse(text) as { data?: unknown[]; musics?: unknown[] } | unknown[];
            const items = Array.isArray(data)
              ? data
              : (Array.isArray(data.musics)
                ? data.musics
                : (Array.isArray(data.data) ? data.data : []));
            pageMusics = items.reduce<Music[]>((acc, item: unknown) => {
              if (typeof item === 'object' && item) {
                const obj = item as Record<string, unknown>;
                const id = String(obj.id || '');
                if (id) {
                  acc.push({
                    id,
                    title: String(obj.title || ''),
                    artist: String(obj.artist || ''),
                    duration: String(obj.duration || ''),
                    tags: Array.isArray(obj.tags) ? obj.tags.map(String) : [],
                  });
                }
              }
              return acc;
            }, []);
          } catch {
            // Fallback to CSV parsing
          }
        }

        if (pageMusics.length === 0 && text.includes('\n')) {
          const lines = text.trim().split(/\r?\n/).filter((line) => line.trim());
          for (let i = 1; i < lines.length; i++) {
            const parts = lines[i].split(',').map((p) => p.trim());
            if (parts.length >= 4 && parts[0]) {
              pageMusics.push({
                id: parts[0],
                title: parts[1],
                artist: parts[2],
                duration: parts[3],
                tags: parts[4] ? parts[4].split(';') : [],
              });
            }
          }
        }

        const sizeBefore = byId.size;
        for (const music of pageMusics) {
          if (!music.id) continue;
          byId.set(music.id, music);
        }
        const newItemsCount = byId.size - sizeBefore;

        const totalPageHeader = res.headers.get('Total-Page');
        if (totalPageHeader) {
          const parsedTotal = Number(totalPageHeader);
          if (Number.isFinite(parsedTotal) && parsedTotal > 0) {
            headerTotalPages = Math.floor(parsedTotal);
          }
        }

        const nextPageHeader = res.headers.get('Next-Page');
        const parsedNext = nextPageHeader && nextPageHeader.trim() !== '' ? Number(nextPageHeader) : NaN;

        if (Number.isFinite(parsedNext) && parsedNext >= 0 && parsedNext !== page) {
          nextPage = parsedNext;
          continue;
        }

        if (headerTotalPages !== null && page + 1 < headerTotalPages) {
          nextPage = page + 1;
          continue;
        }

        if (!nextPageHeader && pageMusics.length > 0 && newItemsCount > 0 && headerTotalPages === null) {
          nextPage = page + 1;
          continue;
        }

        nextPage = null;
      }

      const allMusics = Array.from(byId.values());
      console.log('🎵 Loaded musics:', allMusics.length);
      setAvailableMusics(allMusics);
    } catch (error) {
      console.error('Erreur lors du chargement des musiques:', error);
    }
  }, [apiBaseUrl, token]);

  // Fetch playlist details with tracks (GET /playlists/id)
  const fetchPlaylistDetails = useCallback(async (playlistId: string) => {
    setLoading(true);
    setError(null);
    try {
      const headers: Record<string, string> = {};
      if (token) headers.Authorization = `Bearer ${token}`;
      
      const res = await fetch(buildApiUrl(apiBaseUrl, `/playlists/${playlistId}`), { headers });
      if (res.ok) {
        const data = await res.json() as {
          data?: { id?: string; name?: string; author?: string; musics?: unknown[] };
          id?: string;
          name?: string;
          author?: string;
          musics?: unknown[];
        };
        console.log(`📦 Raw playlist ${playlistId} data:`, data);
        const payload = data.data ?? data;
        console.log('📦 Payload after unwrap:', payload);
        const tracks = normalizePlaylistTracks(payload.musics);
        console.log('✅ Normalized tracks:', tracks);
        setPlaylistTracks(tracks);
        setPlaylistTrackCounts((prev) => ({ ...prev, [playlistId]: tracks.length }));
        setSelectedPlaylist((previous) => {
          if (!previous) return previous;
          if (previous.id !== playlistId) return previous;
          return {
            ...previous,
            name: typeof payload.name === 'string' ? payload.name : previous.name,
            author: typeof payload.author === 'string' ? payload.author : previous.author,
          };
        });
      } else {
        setError(`Erreur ${res.status}: ${res.statusText}`);
      }
    } catch (error) {
      console.error('Erreur lors du chargement de la playlist:', error);
      setError('Erreur de connexion');
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, token]);

  // Create new playlist (POST /playlists)
  const createPlaylist = async () => {
    if (!newPlaylistName.trim()) return;
    
    setSaving(true);
    setError(null);
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers.Authorization = `Bearer ${token}`;
      const author = userEmail || extractAuthorFromToken(token) || 'admin-panel';
      
      const res = await fetch(buildApiUrl(apiBaseUrl, '/playlists'), {
        method: 'POST',
        headers,
        body: JSON.stringify({ name: newPlaylistName, author })
      });
      
      if (res.ok) {
        setNewPlaylistName('');
        setIsCreating(false);
        await fetchPlaylists();
      } else {
        setError(`Erreur ${res.status}: ${res.statusText}`);
      }
    } catch (error) {
      console.error('Erreur lors de la création:', error);
      setError('Erreur de connexion');
    } finally {
      setSaving(false);
    }
  };

  // Delete playlist (DELETE /playlists/id)
  const deletePlaylist = async (playlistId: string) => {
    if (!confirm('Supprimer cette playlist ? Cette action est irréversible.')) return;
    
    setError(null);
    try {
      const headers: Record<string, string> = {};
      if (token) headers.Authorization = `Bearer ${token}`;
      
      const res = await fetch(buildApiUrl(apiBaseUrl, `/playlists/${playlistId}`), {
        method: 'DELETE',
        headers
      });
      
      if (res.ok) {
        if (selectedPlaylist?.id === playlistId) {
          setSelectedPlaylist(null);
          setPlaylistTracks([]);
        }
        await fetchPlaylists();
      } else {
        setError(`Erreur ${res.status}: ${res.statusText}`);
      }
    } catch (error) {
      console.error('Erreur lors de la suppression:', error);
      setError('Erreur de connexion');
    }
  };

  // Save playlist changes (prefer PATCH /playlists/id, fallback PUT)
  const savePlaylist = async () => {
    if (!selectedPlaylist) return;
    
    setSaving(true);
    setError(null);
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers.Authorization = `Bearer ${token}`;
      const fallbackAuthor = userEmail || extractAuthorFromToken(token) || 'admin-panel';
      const payload: { name?: string; author?: string; musics: string[] } = {
        musics: playlistTracks.map((t) => t.id).filter(Boolean)
      };
      if (selectedPlaylist.name?.trim()) payload.name = selectedPlaylist.name;
      payload.author = selectedPlaylist.author || fallbackAuthor;
      
      let res = await fetch(buildApiUrl(apiBaseUrl, `/playlists/${selectedPlaylist.id}`), {
        method: 'PATCH',
        headers,
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        res = await fetch(buildApiUrl(apiBaseUrl, `/playlists/${selectedPlaylist.id}`), {
          method: 'PUT',
          headers,
          body: JSON.stringify(payload)
        });
      }

      if (res.ok) {
        await fetchPlaylists();
      } else {
        setError(`Erreur ${res.status}: ${res.statusText}`);
      }
    } catch (error) {
      console.error('Erreur lors de la sauvegarde:', error);
      const errorMsg = error instanceof Error ? error.message : 'Erreur de connexion';
      setError(`Erreur de connexion: ${errorMsg}`);
    } finally {
      setSaving(false);
    }
  };

  // Add selected musics to playlist
  const addSelectedToPlaylist = () => {
    const musicsToAdd = availableMusics.filter(m => selectedMusicIds.has(m.id));
    const updatedTracks = [...playlistTracks, ...musicsToAdd];
    setPlaylistTracks(updatedTracks);
    if (selectedPlaylist) {
      setPlaylistTrackCounts((prev) => ({ ...prev, [selectedPlaylist.id]: updatedTracks.length }));
    }
    setSelectedMusicIds(new Set());
  };

  const addSingleMusicToPlaylist = (musicId: string) => {
    const music = availableMusics.find((m) => m.id === musicId);
    if (!music) return;
    const updatedTracks = [...playlistTracks, music];
    setPlaylistTracks(updatedTracks);
    if (selectedPlaylist) {
      setPlaylistTrackCounts((prev) => ({ ...prev, [selectedPlaylist.id]: updatedTracks.length }));
    }
  };

  // Remove track from playlist
  const removeTrack = (index: number) => {
    const updated = playlistTracks.filter((_, i) => i !== index);
    setPlaylistTracks(updated);
    if (selectedPlaylist) {
      setPlaylistTrackCounts((prev) => ({ ...prev, [selectedPlaylist.id]: updated.length }));
    }
  };

  // Drag handlers for reordering
  const handleDragStart = (index: number) => {
    setDraggedTrackIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedTrackIndex === null || draggedTrackIndex === index) return;
    
    const newTracks = [...playlistTracks];
    const draggedItem = newTracks[draggedTrackIndex];
    newTracks.splice(draggedTrackIndex, 1);
    newTracks.splice(index, 0, draggedItem);
    
    setPlaylistTracks(newTracks);
    setDraggedTrackIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedTrackIndex(null);
  };

  const moveTrackToPosition = (fromIndex: number, targetPosition: number) => {
    const targetIndex = Math.max(0, Math.min(playlistTracks.length - 1, targetPosition - 1));
    if (fromIndex === targetIndex || fromIndex < 0 || fromIndex >= playlistTracks.length) return;

    const reordered = [...playlistTracks];
    const [moved] = reordered.splice(fromIndex, 1);
    reordered.splice(targetIndex, 0, moved);
    setPlaylistTracks(reordered);
  };

  // Toggle music selection
  const toggleMusicSelection = (musicId: string) => {
    const newSet = new Set(selectedMusicIds);
    if (newSet.has(musicId)) {
      newSet.delete(musicId);
    } else {
      newSet.add(musicId);
    }
    setSelectedMusicIds(newSet);
  };

  // Select all toggle
  const toggleSelectAll = () => {
    if (selectedMusicIds.size === filteredMusics.length && filteredMusics.length > 0) {
      setSelectedMusicIds(new Set());
    } else {
      setSelectedMusicIds(new Set(filteredMusics.map(m => m.id)));
    }
  };

  useEffect(() => {
    fetchPlaylists();
    fetchAvailableMusics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchAvailableMusics]);

  useEffect(() => {
    if (selectedPlaylist) {
      fetchPlaylistDetails(selectedPlaylist.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPlaylist?.id]);

  const filteredMusics = availableMusics.filter(m => {
    const query = searchQuery.toLowerCase();
    return m.title.toLowerCase().includes(query) || m.artist.toLowerCase().includes(query);
  });

  const availableMusicTotalPages = Math.max(1, Math.ceil(filteredMusics.length / availableMusicPageSize));
  const safeAvailableMusicPage = Math.min(availableMusicPage, availableMusicTotalPages - 1);
  const visibleAvailableMusics = useMemo(() => {
    const start = safeAvailableMusicPage * availableMusicPageSize;
    return filteredMusics.slice(start, start + availableMusicPageSize);
  }, [filteredMusics, safeAvailableMusicPage, availableMusicPageSize]);

  const playlistTrackTotalPages = Math.max(1, Math.ceil(playlistTracks.length / playlistTrackPageSize));
  const safePlaylistTrackPage = Math.min(playlistTrackPage, playlistTrackTotalPages - 1);
  const playlistTrackStartIndex = safePlaylistTrackPage * playlistTrackPageSize;
  const visiblePlaylistTracks = playlistTracks.slice(playlistTrackStartIndex, playlistTrackStartIndex + playlistTrackPageSize);

  useEffect(() => {
    setAvailableMusicPage((currentPage) => {
      const nextPage = Math.max(0, Math.min(currentPage, availableMusicTotalPages - 1));
      return nextPage;
    });
  }, [availableMusicTotalPages, availableMusicPageSize]);

  useEffect(() => {
    setAvailableMusicPage(0);
  }, [searchQuery, availableMusicPageSize]);

  useEffect(() => {
    setPlaylistTrackPage((currentPage) => {
      const nextPage = Math.max(0, Math.min(currentPage, playlistTrackTotalPages - 1));
      return nextPage;
    });
  }, [playlistTrackTotalPages, playlistTrackPageSize]);

  useEffect(() => {
    setPlaylistTrackPage(0);
  }, [selectedPlaylist?.id]);

  return (
    <div className="fluff-playlist-manager">
      {error && (
        <div className="fluff-error-banner" onClick={() => setError(null)}>
          ⚠️ {error}
        </div>
      )}
      
      <div className="fluff-playlist-sidebar">
        <div className="fluff-playlist-sidebar-header">
          <h3>Playlists</h3>
          <button onClick={() => setIsCreating(true)} className="fluff-btn-create" title="Créer une playlist">+</button>
        </div>

        {isCreating && (
          <div className="fluff-playlist-create-form">
            <input
              type="text"
              value={newPlaylistName}
              onChange={(e) => setNewPlaylistName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') createPlaylist(); }}
              placeholder="Nom de la playlist"
              className="fluff-input"
              autoFocus
            />
            <div className="fluff-form-actions">
              <button onClick={createPlaylist} disabled={saving || !newPlaylistName.trim()} className="fluff-btn-primary">
                {saving ? '⏳' : 'Créer'}
              </button>
              <button onClick={() => { setIsCreating(false); setNewPlaylistName(''); }} className="fluff-btn-secondary">
                Annuler
              </button>
            </div>
          </div>
        )}

        <div className="fluff-playlist-list">
          {loading && playlists.length === 0 ? (
            <div style={{ padding: '2rem 1rem', textAlign: 'center', color: '#999' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>⏳</div>
              <div>Chargement...</div>
            </div>
          ) : playlists.length === 0 ? (
            <div style={{ padding: '2rem 1rem', textAlign: 'center', color: '#999' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📭</div>
              <div style={{ fontSize: '0.9rem' }}>Aucune playlist</div>
              <div style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: '#ccc' }}>Clique sur + pour en créer une</div>
            </div>
          ) : (
            playlists.map(pl => {
              const inlineCount = countPlaylistTrackIds(pl);
              const trackCount = playlistTrackCounts[pl.id] ?? inlineCount;
              return (
                <div
                  key={pl.id}
                  className={`fluff-playlist-item ${selectedPlaylist?.id === pl.id ? 'active' : ''}`}
                  onClick={() => setSelectedPlaylist(pl)}
                >
                  <div className="fluff-playlist-icon">📁</div>
                  <div className="fluff-playlist-info">
                    <div className="fluff-playlist-name">{pl.name}</div>
                    <div className="fluff-playlist-meta">{trackCount} piste{trackCount > 1 ? 's' : ''}</div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); deletePlaylist(pl.id); }}
                    className="fluff-btn-delete"
                    title="Supprimer"
                  >
                    ✕
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="fluff-playlist-content">
        {selectedPlaylist ? (
          <>
            <div className="fluff-playlist-header">
              <h2>{selectedPlaylist.name}</h2>
              <button
                onClick={savePlaylist}
                disabled={saving}
                className="fluff-btn-save"
                title="Sauvegarder les modifications"
              >
                {saving ? '⏳ Sauvegarde...' : '💾 Sauvegarder'}
              </button>
            </div>

            <div className="fluff-playlist-tabs">
              <button
                className={`fluff-tab ${activeTab === 'tracks' ? 'active' : ''}`}
                onClick={() => setActiveTab('tracks')}
              >
                TRACKS
              </button>
              <button
                className={`fluff-tab ${activeTab === 'albums' ? 'active' : ''}`}
                onClick={() => setActiveTab('albums')}
                disabled
              >
                ALBUMS
              </button>
              <button
                className={`fluff-tab ${activeTab === 'artists' ? 'active' : ''}`}
                onClick={() => setActiveTab('artists')}
                disabled
              >
                ARTISTS
              </button>
              <button
                className={`fluff-tab ${activeTab === 'folders' ? 'active' : ''}`}
                onClick={() => setActiveTab('folders')}
                disabled
              >
                FOLDERS
              </button>
            </div>

            <div className="fluff-playlist-search">
              <label>
                <input
                  type="checkbox"
                  checked={selectedMusicIds.size === filteredMusics.length && filteredMusics.length > 0}
                  onChange={toggleSelectAll}
                />
                Tout sélectionner
              </label>
              <input
                type="text"
                placeholder="Rechercher par titre, artiste..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="fluff-search-input"
              />
              <button
                onClick={addSelectedToPlaylist}
                disabled={selectedMusicIds.size === 0}
                className="fluff-btn-add-selected"
              >
                Ajouter {selectedMusicIds.size > 0 ? `(${selectedMusicIds.size})` : ''}
              </button>
            </div>

            <div className="fluff-playlist-columns">
              <div className="fluff-available-tracks">
                <h3>Musiques disponibles</h3>
                {loading && availableMusics.length === 0 ? (
                  <div className="fluff-loading-state">Chargement...</div>
                ) : filteredMusics.length === 0 ? (
                  <div className="fluff-empty-state">
                    {searchQuery ? 'Aucun résultat' : 'Aucune musique'}
                  </div>
                ) : (
                  <>
                    <div className="fluff-track-list">
                      {visibleAvailableMusics.map(music => (
                      <div
                        key={music.id}
                        className={`fluff-track-row ${selectedMusicIds.has(music.id) ? 'selected' : ''}`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedMusicIds.has(music.id)}
                          onChange={() => toggleMusicSelection(music.id)}
                        />
                        <div className="fluff-track-thumb">🎵</div>
                        <div className="fluff-track-info">
                          <div className="fluff-track-title">{music.title}</div>
                          <div className="fluff-track-artist">{music.artist}</div>
                        </div>
                        <div className="fluff-track-duration">{formatDuration(music.duration) || '—'}</div>
                        <button
                          onClick={(e) => { 
                            e.stopPropagation(); 
                            addSingleMusicToPlaylist(music.id);
                          }}
                          className="fluff-btn-add"
                          title="Ajouter à la playlist"
                        >
                          +
                        </button>
                      </div>
                      ))}
                    </div>
                    <ListPaginationControls
                      totalItems={filteredMusics.length}
                      currentPage={safeAvailableMusicPage}
                      pageSize={availableMusicPageSize}
                      onPageChange={setAvailableMusicPage}
                      onPageSizeChange={setAvailableMusicPageSize}
                      itemLabel="musiques"
                    />
                  </>
                )}
              </div>

              <div className="fluff-playlist-tracks">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <h3 style={{ margin: 0 }}>Pistes dans la playlist ({visiblePlaylistTracks.length}/{playlistTracks.length})</h3>
                </div>
                {playlistTracks.length === 0 ? (
                  <div className="fluff-empty-state">Aucune piste dans cette playlist</div>
                ) : (
                  <div className="fluff-track-list-drag">
                    {visiblePlaylistTracks.map((track, idx) => {
                      const globalIndex = playlistTrackStartIndex + idx;
                      return (
                      <div
                        key={`${track.id}-${globalIndex}`}
                        draggable
                        onDragStart={() => handleDragStart(globalIndex)}
                        onDragOver={(e) => handleDragOver(e, globalIndex)}
                        onDragEnd={handleDragEnd}
                        className={`fluff-track-item ${draggedTrackIndex === globalIndex ? 'dragging' : ''}`}
                      >
                        <span className="fluff-track-order">{globalIndex + 1}</span>
                        <input
                          type="number"
                          min={1}
                          max={playlistTracks.length}
                          defaultValue={globalIndex + 1}
                          className="fluff-track-position-input"
                          title="Position de la piste"
                          onClick={(e) => e.stopPropagation()}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              (e.currentTarget as HTMLInputElement).blur();
                            }
                          }}
                          onBlur={(e) => {
                            const nextPosition = Number(e.currentTarget.value);
                            if (!Number.isFinite(nextPosition)) {
                              e.currentTarget.value = String(globalIndex + 1);
                              return;
                            }
                            moveTrackToPosition(globalIndex, Math.trunc(nextPosition));
                          }}
                        />
                        <div className="fluff-track-handle" title="Glisser pour réorganiser">☰</div>
                        <div className="fluff-track-thumb">🎵</div>
                        <div className="fluff-track-info">
                          <div className="fluff-track-title">{track.title}</div>
                          <div className="fluff-track-artist">{track.artist}</div>
                        </div>
                        <div className="fluff-track-duration">{formatDuration(track.duration) || '—'}</div>
                        <button
                          onClick={() => removeTrack(globalIndex)}
                          className="fluff-btn-remove"
                          title="Retirer de la playlist"
                        >
                          ✕
                        </button>
                      </div>
                      );
                    })}
                  </div>
                )}
                {playlistTracks.length > 0 && (
                  <ListPaginationControls
                    totalItems={playlistTracks.length}
                    currentPage={safePlaylistTrackPage}
                    pageSize={playlistTrackPageSize}
                    onPageChange={setPlaylistTrackPage}
                    onPageSizeChange={(size) => {
                      setPlaylistTrackPageSize(size);
                      setPlaylistTrackPage(0);
                    }}
                    itemLabel="pistes"
                  />
                )}
              </div>
            </div>
          </>
        ) : (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
            textAlign: 'center',
            color: '#999',
            padding: '2rem'
          }}>
            <div style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>🎵</div>
            <h3 style={{ fontSize: '1.2rem', margin: '0 0 0.5rem', color: '#666' }}>Aucune playlist sélectionnée</h3>
            <p style={{ margin: 0, fontSize: '0.95rem', color: '#999' }}>
              Sélectionnez une playlist sur la gauche ou créez-en une nouvelle
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
