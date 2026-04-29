"use client";

import Link from 'next/link';
import { useAuth } from 'react-oidc-context';
import { useMemo } from 'react';
import { useParams } from 'next/navigation';

import DashboardShell from '@/components/admin/DashboardShell';
import { canAccessResource, filterMenuByAccess, findMenuBySlug, firstAccessibleMenuHref } from '@/components/admin/menu';

export default function DashboardSlugPage() {
  const auth = useAuth();
  const params = useParams<{ slug: string }>();
  const slug = params?.slug ?? '';

  const current = useMemo(() => findMenuBySlug(slug), [slug]);

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
  const title = current?.label ?? 'Section';
  const resource = current?.resource ?? slug;
  const authorized = canAccessResource(resource, profile);

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
      activeSlug={slug}
      topbarTag="FluffRadio Admin"
      liveTitle="Section manager"
      pageTitle={title}
      userLabel={auth.user?.profile?.name ?? auth.user?.profile?.email ?? 'Administrateur'}
      onLogout={signOutRedirect}
      breadcrumbs={<><span>Accueil</span><span>/</span><span className="active">{title}</span></>}
    >
      <section className="fluff-table-panel">
        <div style={{ padding: '2rem', textAlign: 'center', color: '#7a7f93' }}>
          <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Section {title}</p>
          <p>Cette section est disponible dans le menu. Branche les routes d&apos;API correspondantes ici.</p>
          <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#aaa' }}>
            Resource de données: <code style={{ background: '#f5f5f5', padding: '0.3rem 0.6rem', borderRadius: '4px' }}>{resource}</code>
          </p>
        </div>
      </section>
    </DashboardShell>
  );
}
