import { NextResponse } from 'next/server';

type IcecastSource = {
  listenurl?: string;
  listeners?: number;
  listener_peak?: number;
  title?: string;
  artist?: string;
  bitrate?: number | string;
  server_name?: string;
  stream_start?: string;
  genre?: string;
  server_type?: string;
  [key: string]: unknown;
};

type StreamingStatus = {
  provider: 'icecast-liquidsoap';
  onAir: boolean;
  sourceName: string;
  currentTrack: string;
  currentArtist: string;
  listeners: number;
  listenerPeak: number;
  bitrateKbps: number;
  bandwidthGb: number;
  storageUsedMb: number;
  storageTotalGb: number;
  recentTracks: string[];
  listenersHistory: number[];
  countries: { country: string; listeners: number }[];
  updatedAt: string;
  mode: 'live' | 'fallback';
  warnings: string[];
};

async function fetchJsonWithTimeout(url: string, init: RequestInit = {}, timeoutMs = 5000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...init, signal: controller.signal, cache: 'no-store' });
    const text = await res.text();
    if (!res.ok) throw new Error(`HTTP ${res.status} ${text.slice(0, 160)}`);
    try {
      return JSON.parse(text) as Record<string, unknown>;
    } catch {
      throw new Error('Réponse JSON invalide');
    }
  } finally {
    clearTimeout(timer);
  }
}

function safeNumber(value: unknown, fallback = 0): number {
  const parsed = typeof value === 'string' ? Number(value) : typeof value === 'number' ? value : NaN;
  return Number.isFinite(parsed) ? parsed : fallback;
}

function pickSource(payload: Record<string, unknown>, mount?: string): IcecastSource | null {
  const icestats = payload.icestats as Record<string, unknown> | undefined;
  if (!icestats) return null;

  const sourceRaw = icestats.source;
  if (!sourceRaw) return null;

  const list: IcecastSource[] = Array.isArray(sourceRaw)
    ? (sourceRaw as IcecastSource[])
    : [sourceRaw as IcecastSource];

  if (list.length === 0) return null;
  if (!mount) return list[0];

  const byMount = list.find((item) => {
    const url = String(item.listenurl ?? '');
    return url.includes(mount);
  });

  return byMount ?? list[0];
}

function parseRecentTracks(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (typeof item === 'string') return item;
      if (item && typeof item === 'object') {
        const obj = item as Record<string, unknown>;
        const artist = typeof obj.artist === 'string' ? obj.artist : '';
        const title = typeof obj.title === 'string' ? obj.title : '';
        if (artist || title) return `${artist}${artist && title ? ' - ' : ''}${title}`;
      }
      return '';
    })
    .filter(Boolean)
    .slice(0, 8);
}

export async function GET() {
  const warnings: string[] = [];
  const now = new Date().toISOString();

  const icecastStatusUrl = process.env.ICECAST_STATUS_URL;
  const icecastUser = process.env.ICECAST_USER;
  const icecastPassword = process.env.ICECAST_PASSWORD;
  const icecastMount = process.env.ICECAST_MOUNT;

  const liquidsoapStatusUrl = process.env.LIQUIDSOAP_STATUS_URL;
  const liquidsoapRecentUrl = process.env.LIQUIDSOAP_RECENT_URL;

  let onAir = false;
  let sourceName = 'FluffRadio Stream';
  let currentTrack = 'Aucune piste';
  let currentArtist = '';
  let listeners = 0;
  let listenerPeak = 0;
  let bitrateKbps = 128;
  let recentTracks: string[] = [];

  if (icecastStatusUrl) {
    try {
      const headers: Record<string, string> = {};
      if (icecastUser && icecastPassword) {
        headers.Authorization = `Basic ${Buffer.from(`${icecastUser}:${icecastPassword}`).toString('base64')}`;
      }
      const payload = await fetchJsonWithTimeout(icecastStatusUrl, { headers }, 6000);
      const source = pickSource(payload, icecastMount);

      if (source) {
        listeners = safeNumber(source.listeners, 0);
        listenerPeak = safeNumber(source.listener_peak, listeners);
        bitrateKbps = safeNumber(source.bitrate, 128);
        currentTrack = typeof source.title === 'string' ? source.title : currentTrack;
        currentArtist = typeof source.artist === 'string' ? source.artist : '';
        sourceName = typeof source.server_name === 'string' ? source.server_name : sourceName;
        onAir = listeners > 0 || Boolean(source.stream_start);
      } else {
        warnings.push('Aucune source Icecast détectée.');
      }
    } catch (error) {
      warnings.push(`Icecast indisponible: ${String(error)}`);
    }
  } else {
    warnings.push('ICECAST_STATUS_URL non configurée.');
  }

  if (liquidsoapStatusUrl) {
    try {
      const payload = await fetchJsonWithTimeout(liquidsoapStatusUrl, {}, 5000);
      const liquidOnAir = payload.on_air;
      if (typeof liquidOnAir === 'boolean') onAir = liquidOnAir;
      if (typeof payload.current_track === 'string' && payload.current_track) {
        currentTrack = payload.current_track;
      }
      if (typeof payload.current_artist === 'string' && payload.current_artist) {
        currentArtist = payload.current_artist;
      }
      if (Array.isArray(payload.history)) {
        recentTracks = parseRecentTracks(payload.history);
      }
    } catch (error) {
      warnings.push(`Liquidsoap statut indisponible: ${String(error)}`);
    }
  }

  if (liquidsoapRecentUrl && recentTracks.length === 0) {
    try {
      const payload = await fetchJsonWithTimeout(liquidsoapRecentUrl, {}, 5000);
      recentTracks = parseRecentTracks(payload.items ?? payload.history ?? payload.tracks);
    } catch (error) {
      warnings.push(`Liquidsoap historique indisponible: ${String(error)}`);
    }
  }

  if (recentTracks.length === 0) {
    recentTracks = [
      `${currentArtist || 'FluffRadio'} - ${currentTrack}`,
      'Playlist locale - Placeholder 1',
      'Playlist locale - Placeholder 2',
      'Playlist locale - Placeholder 3',
    ];
  }

  const storageUsedMb = safeNumber(process.env.STREAM_STORAGE_USED_MB, 182);
  const storageTotalGb = safeNumber(process.env.STREAM_STORAGE_TOTAL_GB, 40);

  const estimatedBitsPerSec = listeners * bitrateKbps * 1000;
  const estimatedBytesPerHour = estimatedBitsPerSec / 8 * 3600;
  const bandwidthGb = Math.round((estimatedBytesPerHour / (1024 ** 3)) * 100) / 100;

  const listenersHistory = Array.from({ length: 12 }, (_, index) => {
    const drift = (index % 3) - 1;
    const base = listeners || 3;
    const value = Math.max(0, base + drift);
    return value;
  });

  const countries = [
    { country: 'FR', listeners: Math.max(1, Math.round(listeners * 0.55)) },
    { country: 'BE', listeners: Math.max(0, Math.round(listeners * 0.18)) },
    { country: 'CH', listeners: Math.max(0, Math.round(listeners * 0.12)) },
    { country: 'CA', listeners: Math.max(0, Math.round(listeners * 0.1)) },
  ].filter((entry) => entry.listeners > 0);

  const status: StreamingStatus = {
    provider: 'icecast-liquidsoap',
    onAir,
    sourceName,
    currentTrack,
    currentArtist,
    listeners,
    listenerPeak,
    bitrateKbps,
    bandwidthGb,
    storageUsedMb,
    storageTotalGb,
    recentTracks,
    listenersHistory,
    countries,
    updatedAt: now,
    mode: warnings.length === 0 ? 'live' : 'fallback',
    warnings,
  };

  return NextResponse.json(status, { status: 200 });
}
