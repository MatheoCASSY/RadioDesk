'use client';

import { useAuth } from 'react-oidc-context';
import Link from 'next/link';
import DashboardShell from '@/components/admin/DashboardShell';
import { canAccessResource, filterMenuByAccess, firstAccessibleMenuHref } from '@/components/admin/menu';
import PlaylistManager from '@/components/admin/PlaylistManager';

export default function PlaylistsPage() {
  const auth = useAuth();

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
  if (auth.error) return <div className="min-h-screen flex items-center justify-center">Erreur: {String(auth.error)}</div>;

  if (!auth.isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <button onClick={() => auth.signinRedirect()} className="btn-fluff">Se connecter</button>
      </div>
    );
  }

  const profile = (auth.user?.profile ?? null) as Record<string, unknown> | null;
  const visibleMenu = filterMenuByAccess(profile);
  const fallbackHref = firstAccessibleMenuHref(profile);
  const authorized = canAccessResource('playlists', profile);

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

  const token = auth.user?.access_token ?? auth.user?.id_token ?? '';
  const userEmail = auth.user?.profile?.email ?? auth.user?.profile?.preferred_username ?? 'admin';
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'https://nu8n9r0hl5.execute-api.eu-west-1.amazonaws.com';

  return (
    <DashboardShell
      visibleMenu={visibleMenu}
      activeSlug="playlists"
      topbarTag="FluffRadio - Playlists"
      liveTitle="Playlist Manager"
      pageTitle="Playlists"
      userLabel={auth.user?.profile?.name ?? auth.user?.profile?.email ?? 'Admin'}
      onLogout={signOutRedirect}
      breadcrumbs={<><span>Accueil</span><span>/</span><span className="active">Playlists</span></>}
    >
      <PlaylistManager apiBaseUrl={apiBaseUrl} token={token} userEmail={userEmail} />
    </DashboardShell>
  );
}
