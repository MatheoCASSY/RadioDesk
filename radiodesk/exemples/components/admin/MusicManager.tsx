"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import S3Uploader from '../S3Uploader';
import { getS3ObjectAsBlob, initS3Download } from '@/lib/s3Download';
import { formatDuration } from '@/lib/formatDuration';
import ListPaginationControls, { type PageSize } from './ListPaginationControls';

type Music = {
  id: string;
  title: string;
  artist?: string;
  album?: string;
  genre?: string;
  year?: string;
  duration?: string;
  tags?: string[];
  uploadedAt?: string;
  size?: number;
};

type MusicManagerProps = {
  apiBaseUrl: string;
  token?: string;
};

function buildApiUrl(apiBaseUrl: string, path: string) {
  const useProxy = process.env.NEXT_PUBLIC_API_PROXY !== '0';
  if (useProxy) return `/api${path}`;
  return `${apiBaseUrl.replace(/\/+$/, '')}${path}`;
}

function toStringOrEmpty(value: unknown): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return '';
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function pickFirstString(obj: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = obj[key];
    const normalized = toStringOrEmpty(value).trim();
    if (normalized) return normalized;
  }
  return '';
}

function mapMusicRecord(item: unknown): Music {
  const obj = asRecord(item);
  const metadata = asRecord(obj.metadata);

  const id = pickFirstString(obj, ['id', 'ID', 'Id', 'music_id', 'musicId', 'uuid', 'key'])
    || pickFirstString(metadata, ['id', 'music_id']);

  const title = pickFirstString(obj, ['title', 'name', 'filename', 'file_name'])
    || pickFirstString(metadata, ['title', 'name'])
    || 'Sans titre';

  const artist = pickFirstString(obj, ['artist', 'author'])
    || pickFirstString(metadata, ['artist', 'author']);

  const album = pickFirstString(obj, ['album'])
    || pickFirstString(metadata, ['album']);

  const genre = pickFirstString(obj, ['genre'])
    || pickFirstString(metadata, ['genre']);

  const year = pickFirstString(obj, ['year'])
    || pickFirstString(metadata, ['year']);

  const duration = pickFirstString(obj, ['duration', 'length'])
    || pickFirstString(metadata, ['duration', 'length']);

  const uploadedAt = pickFirstString(obj, ['uploadedAt', 'uploaded_at', 'createdAt', 'created_at'])
    || pickFirstString(metadata, ['uploadedAt', 'uploaded_at', 'createdAt', 'created_at']);

  const tagsRaw = obj.tags ?? metadata.tags;
  const tags = Array.isArray(tagsRaw)
    ? tagsRaw.map((tag) => toStringOrEmpty(tag).trim()).filter(Boolean)
    : (typeof tagsRaw === 'string'
      ? tagsRaw.split(/[;,]/).map((tag) => tag.trim()).filter(Boolean)
      : []);

  return { id, title, artist, album, genre, year, duration, uploadedAt, tags };
}

function splitTags(raw: string): string[] {
  return raw
    .split(/[;,]/)
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function parseCsvLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (char === ',' && !inQuotes) {
      result.push(current.trim());
      current = '';
      continue;
    }
    current += char;
  }

  result.push(current.trim());
  return result;
}

function parseCsvRows(text: string): Music[] {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length === 0) return [];

  if (lines.length === 1) {
    const maybeSingle = parseCsvLine(lines[0]);
    if (maybeSingle.length >= 2) {
      return [
        {
          id: maybeSingle[0] ?? '',
          title: maybeSingle[1] ?? 'Sans titre',
          artist: maybeSingle[2] ?? '',
          duration: maybeSingle[3] ?? '',
          uploadedAt: maybeSingle[4] ?? '',
        },
      ].filter((m) => Boolean(m.id));
    }
    return [];
  }

  const headers = parseCsvLine(lines[0]);
  const hasHeaderRow = headers.some((h) => /id|title|name|artist|duration|created|uploaded/i.test(h));
  const startIndex = hasHeaderRow ? 1 : 0;

  const rows = lines.slice(startIndex).map((line) => {
    const columns = parseCsvLine(line);
    const record: Record<string, unknown> = {};
    headers.forEach((header, index) => {
      const key = (header || `col_${index}`).trim();
      record[key] = columns[index] ?? '';
    });

    if (!hasHeaderRow) {
      record.id = columns[0] ?? '';
      record.title = columns[1] ?? '';
      record.artist = columns[2] ?? '';
      record.duration = columns[3] ?? '';
      record.uploadedAt = columns[4] ?? '';
    }

    return mapMusicRecord(record);
  });

  return rows.filter((m) => Boolean(m.id));
}

function parseMusicResponse(text: string, contentType: string): { rows: Music[]; inferredTotalPages: number | null } {
  const normalizedContentType = contentType.toLowerCase();
  let rows: Music[] = [];
  let inferredTotalPages: number | null = null;

  if (normalizedContentType.includes('application/json')) {
    try {
      const parsed = JSON.parse(text) as unknown;
      if (parsed && typeof parsed === 'object') {
        const parsedObj = parsed as Record<string, unknown>;
        const list = Array.isArray(parsedObj.musics)
          ? (parsedObj.musics as unknown[])
          : (Array.isArray(parsedObj.data) ? (parsedObj.data as unknown[]) : null);

        if (list) {
          rows = list.map((item) => mapMusicRecord(item)).filter((m) => Boolean(m.id));
        }

        const metadata = parsedObj.metadata;
        if (metadata && typeof metadata === 'object') {
          const md = metadata as Record<string, unknown>;
          const totalFromMetadata =
            typeof md.total_pages === 'number'
              ? md.total_pages
              : (typeof md.total_pages === 'string' ? Number(md.total_pages) : NaN);

          if (Number.isFinite(totalFromMetadata) && totalFromMetadata > 0) {
            inferredTotalPages = Math.floor(totalFromMetadata);
          }
        }
      } else if (Array.isArray(parsed)) {
        rows = (parsed as Array<Record<string, unknown>>)
          .map((obj) => mapMusicRecord(obj))
          .filter((m) => Boolean(m.id));
      }
    } catch {
      rows = [];
    }
  } else {
    rows = parseCsvRows(text);
  }

  if (rows.length === 0 && text.includes('\n')) {
    rows = parseCsvRows(text);
  }

  return { rows, inferredTotalPages };
}

export default function MusicManager({ apiBaseUrl, token }: MusicManagerProps) {
  const [musics, setMusics] = useState<Music[]>([]);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState<PageSize>(25);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [autoReload, setAutoReload] = useState(false);
  const [reloadMs, setReloadMs] = useState(15000);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [playerUrl, setPlayerUrl] = useState<string | null>(null);
  const [editingMusic, setEditingMusic] = useState<Music | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editArtist, setEditArtist] = useState('');
  const [editAlbum, setEditAlbum] = useState('');
  const [editGenre, setEditGenre] = useState('');
  const [editYear, setEditYear] = useState('');
  const [editTags, setEditTags] = useState('');
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const stopMusic = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setPlayerUrl(null);
    setPlayingId(null);
  }, [audioUrl]);

  useEffect(() => {
    const audioEl = audioRef.current;
    return () => {
      if (audioEl) {
        audioEl.pause();
      }
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  const fetchMusics = useCallback(async (silent = false) => {
    setLoading(true);
    try {
      const headers: HeadersInit = {
        Accept: 'application/json, text/csv;q=0.9',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };

      const byId = new Map<string, Music>();
      const visitedPages = new Set<number>();
      let nextPage: number | null = 0;
      let headerTotalPages: number | null = null;
      let metadataTotalPages: number | null = null;

      for (let guard = 0; guard < 500 && nextPage !== null; guard++) {
        const currentPage: number = nextPage;
        if (visitedPages.has(currentPage)) break;
        visitedPages.add(currentPage);

        const url = buildApiUrl(apiBaseUrl, `/musics?page=${currentPage}`);
        const response = await fetch(url, { headers, cache: 'no-store' });
        if (!response.ok) throw new Error(`Chargement échoue page ${currentPage + 1}: ${response.status}`);

        const text = await response.text();
        const contentType = response.headers.get('content-type') || '';
        const { rows, inferredTotalPages } = parseMusicResponse(text, contentType);

        if (inferredTotalPages && inferredTotalPages > 0) {
          metadataTotalPages = inferredTotalPages;
        }

        const totalPageHeader = response.headers.get('Total-Page');
        if (totalPageHeader) {
          const parsedTotal = Number(totalPageHeader);
          if (Number.isFinite(parsedTotal) && parsedTotal > 0) {
            headerTotalPages = Math.floor(parsedTotal);
          }
        }

        const sizeBefore = byId.size;
        for (const row of rows) {
          if (!row.id) continue;
          byId.set(row.id, row);
        }
        const newItemsCount = byId.size - sizeBefore;

        const nextPageHeader = response.headers.get('Next-Page');
        const parsedNextHeader = nextPageHeader !== null && nextPageHeader.trim() !== ''
          ? Number(nextPageHeader)
          : NaN;

        if (Number.isFinite(parsedNextHeader) && parsedNextHeader >= 0 && parsedNextHeader !== currentPage) {
          nextPage = parsedNextHeader;
          continue;
        }

        const knownTotalPages = headerTotalPages ?? metadataTotalPages;
        if (knownTotalPages !== null && currentPage + 1 < knownTotalPages) {
          nextPage = currentPage + 1;
          continue;
        }

        if (!nextPageHeader && rows.length > 0 && newItemsCount > 0 && knownTotalPages === null) {
          nextPage = currentPage + 1;
          continue;
        }

        nextPage = null;
      }

      const allRows = Array.from(byId.values());
      setMusics(allRows);
      setPage(0);
      if (!silent) setMessage(`Liste chargee: ${allRows.length} piste(s).`);
    } catch (error) {
      if (!silent) setMessage(`Erreur chargement: ${String(error)}`);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, token]);

  useEffect(() => {
    void fetchMusics(false);
  }, [fetchMusics]);

  useEffect(() => {
    if (!autoReload) return;
    const intervalMs = Math.max(3000, reloadMs);
    const id = setInterval(() => {
      void fetchMusics(true);
    }, intervalMs);
    return () => clearInterval(id);
  }, [autoReload, reloadMs, fetchMusics]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return musics;
    return musics.filter((m) =>
      m.title.toLowerCase().includes(term) ||
      (m.artist?.toLowerCase().includes(term) ?? false) ||
      (m.tags?.some((tag) => tag.toLowerCase().includes(term)) ?? false)
    );
  }, [musics, query]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.max(0, Math.min(page, totalPages - 1));
  const visibleMusics = useMemo(() => {
    const start = safePage * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, safePage, pageSize]);

  useEffect(() => {
    if (page !== safePage) {
      setPage(safePage);
    }
  }, [page, safePage]);

  useEffect(() => {
    setPage(0);
  }, [query, pageSize]);

  const deleteMusic = async (id: string) => {
    if (!confirm('Confirmer la suppression ?')) return;
    setLoading(true);
    try {
      const url = buildApiUrl(apiBaseUrl, `/musics/${encodeURIComponent(id)}`);
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const response = await fetch(url, { method: 'DELETE', headers, cache: 'no-store' });
      if (!response.ok) throw new Error(`Suppression échouée: ${response.status}`);
      setMessage('Piste supprimée.');
      await fetchMusics(true);
    } catch (error) {
      setMessage(`Erreur suppression: ${String(error)}`);
    } finally {
      setLoading(false);
    }
  };

  const playMusic = async (id: string) => {
    setLoading(true);
    try {
      stopMusic();
      const session = await initS3Download(id, token ?? undefined);
      const object = await getS3ObjectAsBlob(session);
      const contentType = (object.blob.type || session.contentType || '').toLowerCase();
      const buffer = await object.blob.arrayBuffer();

      if (contentType.includes('application/json') || contentType.includes('text/html') || contentType.includes('text/plain')) {
        const text = new TextDecoder().decode(buffer);
        throw new Error(`Réponse non audio: ${text.slice(0, 180)}`);
      }

      let mimeType = contentType.split(';')[0].trim();
      if (!mimeType || !mimeType.startsWith('audio/')) {
        const bytes = new Uint8Array(buffer);
        const isMp3 = bytes.length > 3 && bytes[0] === 0x49 && bytes[1] === 0x44 && bytes[2] === 0x33;
        const isOgg = bytes.length > 4 && bytes[0] === 0x4f && bytes[1] === 0x67 && bytes[2] === 0x67 && bytes[3] === 0x53;
        const isFlac = bytes.length > 4 && bytes[0] === 0x66 && bytes[1] === 0x4c && bytes[2] === 0x61 && bytes[3] === 0x43;
        const isWav = bytes.length > 12 && bytes[0] === 0x52 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x46 && bytes[8] === 0x57 && bytes[9] === 0x41 && bytes[10] === 0x56 && bytes[11] === 0x45;

        if (isMp3) mimeType = 'audio/mpeg';
        else if (isOgg) mimeType = 'audio/ogg';
        else if (isFlac) mimeType = 'audio/flac';
        else if (isWav) mimeType = 'audio/wav';
        else mimeType = 'audio/mpeg';
      }

      const blob = new Blob([buffer], { type: mimeType });
      const objectUrl = URL.createObjectURL(blob);
      setAudioUrl(objectUrl);
      setPlayerUrl(objectUrl);
      setPlayingId(id);
      setMessage('Piste chargée.');
    } catch (error) {
      setMessage(`Erreur lecture: ${String(error)}`);
    } finally {
      setLoading(false);
    }
  };

  const openEdit = (music: Music) => {
    setEditingMusic(music);
    setEditTitle(music.title ?? '');
    setEditArtist(music.artist ?? '');
    setEditAlbum(music.album ?? '');
    setEditGenre(music.genre ?? '');
    setEditYear(music.year ?? '');
    setEditTags((music.tags ?? []).join(', '));
  };

  const closeEdit = () => {
    setEditingMusic(null);
    setEditTitle('');
    setEditArtist('');
    setEditAlbum('');
    setEditGenre('');
    setEditYear('');
    setEditTags('');
  };

  const editTagsPreview = useMemo(() => splitTags(editTags), [editTags]);

  const hasMetadataChanges = useMemo(() => {
    if (!editingMusic) return false;

    const currentTitle = (editingMusic.title ?? '').trim();
    const currentArtist = (editingMusic.artist ?? '').trim();
    const currentAlbum = (editingMusic.album ?? '').trim();
    const currentGenre = (editingMusic.genre ?? '').trim();
    const currentYear = (editingMusic.year ?? '').trim();
    const currentTags = (editingMusic.tags ?? []).map((tag) => tag.trim()).filter(Boolean).join('|');

    const nextTitle = editTitle.trim();
    const nextArtist = editArtist.trim();
    const nextAlbum = editAlbum.trim();
    const nextGenre = editGenre.trim();
    const nextYear = editYear.trim();
    const nextTags = splitTags(editTags).join('|');

    return (
      currentTitle !== nextTitle
      || currentArtist !== nextArtist
      || currentAlbum !== nextAlbum
      || currentGenre !== nextGenre
      || currentYear !== nextYear
      || currentTags !== nextTags
    );
  }, [editingMusic, editTitle, editArtist, editAlbum, editGenre, editYear, editTags]);

  const saveEdit = async () => {
    if (!editingMusic) return;
    const yearInput = editYear.trim();
    if (yearInput) {
      const parsedYear = Number(yearInput);
      if (!Number.isFinite(parsedYear)) {
        setMessage('Annee invalide: entrez une valeur numerique.');
        return;
      }
    }

    if (!hasMetadataChanges) {
      setMessage('Aucune modification detectee.');
      return;
    }

    setLoading(true);
    try {
      const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
      const patchPayload: Record<string, unknown> = {};

      const normalizedTags = splitTags(editTags);
      const normalizedTitle = editTitle.trim();
      const normalizedArtist = editArtist.trim();
      const normalizedAlbum = editAlbum.trim();
      const normalizedGenre = editGenre.trim();
      const normalizedYear = editYear.trim();

      if (normalizedTitle) patchPayload.title = normalizedTitle;
      if (normalizedArtist) patchPayload.artist = normalizedArtist;
      if (normalizedAlbum) patchPayload.album = normalizedAlbum;
      if (normalizedGenre) patchPayload.genre = normalizedGenre;
      if (normalizedYear) patchPayload.year = Math.trunc(Number(normalizedYear));
      patchPayload.tags = normalizedTags;

      const patchResponse = await fetch(buildApiUrl(apiBaseUrl, `/musics/${encodeURIComponent(editingMusic.id)}`), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(patchPayload),
        cache: 'no-store',
      });

      if (!patchResponse.ok) {
        const txt = await patchResponse.text().catch(() => '');
        throw new Error(`Maj métadonnées échouée: ${patchResponse.status} ${txt}`);
      }

      setMessage('Metadonnees mises a jour avec succes.');
      closeEdit();
      await fetchMusics(true);
    } catch (error) {
      setMessage(`Erreur modification: ${String(error)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="fluff-table-panel">
      <div className="fluff-table-head">
        <h2>Fichiers audio</h2>
        <div className="fluff-table-controls">
          <input
            type="search"
            placeholder="Recherche par titre/artiste"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.9rem' }}>
            <input
              type="checkbox"
              checked={autoReload}
              onChange={(e) => setAutoReload(e.target.checked)}
            />
            Auto-reload
          </label>
          <select
            value={reloadMs}
            onChange={(e) => setReloadMs(Number(e.target.value))}
            disabled={!autoReload}
            title="Intervalle de rafraîchissement"
          >
            <option value={5000}>5s</option>
            <option value={10000}>10s</option>
            <option value={15000}>15s</option>
            <option value={30000}>30s</option>
            <option value={60000}>60s</option>
          </select>
        </div>
      </div>

      {message ? <div className="fluff-banner">{message}</div> : null}

      <div className="fluff-banner" style={{ marginTop: '1rem' }}>
        <strong>📤 Uploader des fichiers audio</strong>
        <S3Uploader
          token={token ?? ''}
          isProgrammateur={true}
          onDiagnosticMessage={(diagnostic) => {
            setMessage(diagnostic);
          }}
          onUpload={(ids) => {
            setMessage(`✅ ${ids.length} fichier(s) uploadé(s) !`);
            setTimeout(() => { void fetchMusics(false); }, 500);
          }}
        />
      </div>

      {editingMusic ? (
        <div className="fluff-banner fluff-metadata-editor">
          <div className="fluff-metadata-editor-head">
            <strong>Correction des metadonnees</strong>
            <span>ID: {editingMusic.id}</span>
          </div>

          <div className="fluff-metadata-grid">
            <label>
              <span>Titre</span>
              <input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                placeholder="Titre de la piste"
              />
            </label>
            <label>
              <span>Artiste</span>
              <input
                value={editArtist}
                onChange={(e) => setEditArtist(e.target.value)}
                placeholder="Nom de l'artiste"
              />
            </label>
            <label>
              <span>Album (optionnel)</span>
              <input
                value={editAlbum}
                onChange={(e) => setEditAlbum(e.target.value)}
                placeholder="Nom de l'album"
              />
            </label>
            <label>
              <span>Genre (optionnel)</span>
              <input
                value={editGenre}
                onChange={(e) => setEditGenre(e.target.value)}
                placeholder="Rap, Pop, Electro..."
              />
            </label>
            <label>
              <span>Annee (optionnel)</span>
              <input
                value={editYear}
                onChange={(e) => setEditYear(e.target.value)}
                placeholder="Ex: 2024"
                inputMode="numeric"
                pattern="[0-9]*"
              />
            </label>
            <label className="fluff-metadata-tags-field">
              <span>Tags</span>
              <input
                value={editTags}
                onChange={(e) => setEditTags(e.target.value)}
                placeholder="Tags separes par des virgules (ex: rap, fr, 2010s)"
              />
              <small>Utilisez des virgules ou des points-virgules pour separer les tags.</small>
            </label>
          </div>

          <div className="fluff-metadata-preview">
            <span>Apercu tags:</span>
            <div className="fluff-metadata-preview-tags">
              {editTagsPreview.length > 0
                ? editTagsPreview.map((tag) => (
                  <span key={tag} className="fluff-tag">{tag}</span>
                ))
                : <span className="fluff-metadata-empty">Aucun tag</span>}
            </div>
          </div>

          <div className="fluff-metadata-actions">
            <button onClick={saveEdit} disabled={loading || !hasMetadataChanges}>Sauvegarder</button>
            <button onClick={closeEdit} disabled={loading}>Annuler</button>
          </div>
        </div>
      ) : null}

      {playerUrl ? (
        <div className="fluff-banner" style={{ display: 'grid', gap: '0.5rem' }}>
          <strong>Lecteur</strong>
          <audio
            ref={audioRef}
            controls
            autoPlay
            src={playerUrl}
            onEnded={() => setPlayingId(null)}
            onError={() => setMessage('Lecture non supportée par le navigateur pour ce format.')}
            style={{ width: '100%' }}
          />
          <div>
            <button onClick={stopMusic}>⏹ Stop</button>
          </div>
        </div>
      ) : null}

      <div className="fluff-table-wrapper">
        <table className="fluff-table">
          <thead>
            <tr>
              <th>Titre</th>
              <th>Artiste</th>
              <th>Durée</th>
              <th>Ajouté</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleMusics.map((music) => (
              <tr key={music.id}>
                <td>{music.title}</td>
                <td>{music.artist || '—'}</td>
                <td>{formatDuration(music.duration) || '—'}</td>
                <td>{music.uploadedAt || '—'}</td>
                <td>
                  <div className="fluff-actions">
                    <button
                      onClick={() => (playingId === music.id ? stopMusic() : playMusic(music.id))}
                      disabled={loading}
                      title={playingId === music.id ? 'Stop' : 'Lire'}
                    >
                      {playingId === music.id ? '⏹' : '▶'}
                    </button>
                    <button
                      onClick={() => openEdit(music)}
                      disabled={loading}
                      title="Modifier"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => deleteMusic(music.id)}
                      disabled={loading}
                      title="Supprimer"
                    >
                      🗑
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ListPaginationControls
        totalItems={filtered.length}
        currentPage={safePage}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
        disabled={loading}
        itemLabel="pistes"
      />
    </section>
  );
}
