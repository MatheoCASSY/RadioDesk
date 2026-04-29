"use client";

import { useEffect, useState } from 'react';
import { useAuth } from 'react-oidc-context';
import Link from 'next/link';
import DashboardShell from '@/components/admin/DashboardShell';
import { canAccessResource, filterMenuByAccess, firstAccessibleMenuHref } from '@/components/admin/menu';

type StreamingStatus = {
  provider: string;
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

export default function DashboardPage() {
  const auth = useAuth();
  const [streaming, setStreaming] = useState<StreamingStatus | null>(null);
  const [streamBusy, setStreamBusy] = useState<null | 'start' | 'stop' | 'skip' | 'reload'>(null);
  const [banner, setBanner] = useState('');

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

  useEffect(() => {
    if (!auth.isAuthenticated) return;

    let isCancelled = false;

    const fetchStreaming = async () => {
      try {
        const res = await fetch('/api/streaming/status', { cache: 'no-store' });
        const payload = await res.json();
        if (!res.ok) throw new Error(payload?.error ?? 'Erreur status streaming');
        if (!isCancelled) setStreaming(payload as StreamingStatus);
      } catch (error) {
        if (!isCancelled) setBanner(`Streaming status indisponible: ${String(error)}`);
      }
    };

    void fetchStreaming();
    const intervalId = window.setInterval(fetchStreaming, 15000);

    return () => {
      isCancelled = true;
      window.clearInterval(intervalId);
    };
  }, [auth.isAuthenticated]);

  const runStreamControl = async (action: 'start' | 'stop' | 'skip' | 'reload') => {
    setStreamBusy(action);
    try {
      const res = await fetch('/api/streaming/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(payload?.error ?? 'Contrôle streaming en erreur');
      setBanner(typeof payload?.message === 'string' ? payload.message : `Action ${action} envoyée.`);
      const refresh = await fetch('/api/streaming/status', { cache: 'no-store' });
      if (refresh.ok) {
        const data = await refresh.json();
        setStreaming(data as StreamingStatus);
      }
    } catch (error) {
      setBanner(`Contrôle streaming échoué: ${String(error)}`);
    } finally {
      setStreamBusy(null);
    }
  };

  const maxHistory = Math.max(...(streaming?.listenersHistory ?? [1]), 1);

  if (auth.isLoading) return <div className="min-h-screen flex items-center justify-center">Chargement...</div>;
  if (auth.error) return <div className="min-h-screen flex items-center justify-center">Erreur d&apos;authentification: {String(auth.error)}</div>;

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
  const authorized = canAccessResource('dashboard', profile);

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
      activeHref="/dashboard"
      topbarTag="FluffRadio Admin"
      liveTitle="Enjoy it"
      pageTitle="Webradio Control Center"
      userLabel={auth.user?.profile?.name ?? auth.user?.profile?.email ?? 'Administrateur'}
      onLogout={signOutRedirect}
    >
      {banner && <div className="fluff-banner">{banner}</div>}

      <div className="fluff-card-grid">
        <article className="fluff-action-card">
          <h3>Fichiers audio</h3>
          <p>Uploader, éditer et gérer la bibliothèque audio.</p>
          <Link href="/dashboard/fichiers-audio"><button>+</button></Link>
        </article>
        <article className="fluff-action-card">
          <h3>Playlists</h3>
          <p>Organiser les séquences musicales de diffusion.</p>
          <Link href="/dashboard/playlists"><button>+</button></Link>
        </article>
        <article className="fluff-action-card">
          <h3>Programmations</h3>
          <p>Préparer les contenus à diffuser par créneau.</p>
          <Link href="/dashboard/programmations"><button>+</button></Link>
        </article>
        <article className="fluff-action-card">
          <h3>Cache</h3>
          <p>Inspecter et mettre à jour le cache des données.</p>
          <Link href="/api/admin/cache"><button>+</button></Link>
        </article>
      </div>

      <section className="fluff-stream-grid">
        <article className="fluff-stream-panel fluff-stream-main">
          <div className="fluff-stream-head">
            <h2>Streaming Manager (Icecast + Liquidsoap)</h2>
            <span className={`fluff-live-state ${streaming?.onAir ? 'on' : 'off'}`}>{streaming?.onAir ? 'On Air' : 'Off Air'}</span>
          </div>
          <div className="fluff-stream-controls">
            <button disabled={streamBusy !== null} onClick={() => runStreamControl('start')}>Start</button>
            <button disabled={streamBusy !== null} onClick={() => runStreamControl('stop')}>Stop</button>
            <button disabled={streamBusy !== null} onClick={() => runStreamControl('skip')}>Skip</button>
            <button disabled={streamBusy !== null} onClick={() => runStreamControl('reload')}>Reload</button>
          </div>
          <div className="fluff-now-playing">
            <div className="cover">♪</div>
            <div>
              <div className="title">{streaming?.currentTrack ?? 'Chargement piste...'}</div>
              <div className="artist">{streaming?.currentArtist || streaming?.sourceName || 'Flux principal FluffRadio'}</div>
              <div className="meta">{streaming?.bitrateKbps ?? 128} kbps • Pic {streaming?.listenerPeak ?? 0} auditeurs</div>
            </div>
          </div>
        </article>

        <article className="fluff-stream-panel metric">
          <h3>Listeners</h3>
          <div className="value">{streaming?.listeners ?? 0}</div>
          <p>Auditeurs en direct</p>
        </article>

        <article className="fluff-stream-panel metric">
          <h3>Bandwidth</h3>
          <div className="value">{(streaming?.bandwidthGb ?? 0).toFixed(2)} GB/h</div>
          <p>Estimation selon bitrate et auditeurs</p>
        </article>

        <article className="fluff-stream-panel metric">
          <h3>Storage</h3>
          <div className="value">{streaming?.storageUsedMb ?? 0} MB / {streaming?.storageTotalGb ?? 0} GB</div>
          <p>Média local / bucket de diffusion</p>
        </article>

        <article className="fluff-stream-panel">
          <h3>Recently played</h3>
          <ul className="fluff-recent-list">
            {(streaming?.recentTracks ?? []).slice(0, 6).map((track) => (
              <li key={track}>{track}</li>
            ))}
          </ul>
        </article>

        <article className="fluff-stream-panel">
          <h3>Listeners trend</h3>
          <div className="fluff-history-bars">
            {(streaming?.listenersHistory ?? []).map((value, index) => (
              <div key={`${value}-${index}`} className="bar-wrap">
                <div className="bar" style={{ height: `${Math.max(10, (value / maxHistory) * 100)}%` }} />
                <span>{value}</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </DashboardShell>
  );
}
