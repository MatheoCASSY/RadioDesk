'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useAuth } from 'react-oidc-context';
import { canAccessResource, filterMenuByAccess, firstAccessibleMenuHref } from '@/components/admin/menu';

type Props = {
  slug: string;
  title: string;
  description: string;
};

export default function AdminStubSectionPage({ slug, title, description }: Props) {
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
  const authorized = canAccessResource(slug, profile);

  if (!authorized) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center max-w-xl">
          <h2 className="text-2xl font-semibold mb-4">Accès refusé</h2>
          <p className="mb-6 text-zinc-600">Votre groupe IAM ne permet pas d&apos;accéder à cette section.</p>
          <Link href={fallbackHref} className="rounded-full bg-zinc-900 text-white px-6 py-2 inline-block">Retour au dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="fluff-dashboard-shell">
      <aside className="fluff-sidebar">
        <div className="fluff-sidebar-brand">
          <Image
            src="/chartegraphique/FluffRadio-CharteGraphique-Noka-x-Pawl/FluffRadio-CG-Full/LivreePNG-FluffRadio-Communication-Livery/FluffRadio-logo-color-livery.png"
            alt="FluffRadio"
            width={170}
            height={44}
            priority
          />
        </div>

        <div className="fluff-live-card">
          <div className="fluff-live-pill">LIVE STREAM</div>
          <div className="fluff-live-title">{title}</div>
          <div className="fluff-live-ready">READY</div>
        </div>

        <nav className="fluff-nav">
          {visibleMenu.map((item) => (
            <Link
              key={item.slug || item.resource || item.href}
              className={`fluff-nav-item ${item.slug === slug ? 'active' : ''}`}
              href={item.href}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      <section className="fluff-dashboard-main">
        <div className="fluff-topbar">
          <div className="fluff-topbar-tag">FluffRadio - {title}</div>
          <div className="fluff-topbar-user">
            <span className="fluff-topbar-name">{auth.user?.profile?.name ?? auth.user?.profile?.email ?? 'Admin'}</span>
            <button className="fluff-topbar-logout" onClick={signOutRedirect}>Déconnexion</button>
          </div>
        </div>

        <main className="fluff-content">
          <h1 className="fluff-page-title">{title}</h1>
          <div className="fluff-breadcrumbs">
            <span>Accueil</span>
            <span>/</span>
            <span className="active">{title}</span>
          </div>

          <section className="fluff-table-panel">
            <div style={{ padding: '2rem', textAlign: 'center', color: '#7a7f93' }}>
              <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>{description}</p>
              <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#aaa' }}>
                Ressource de section: <code style={{ background: '#f5f5f5', padding: '0.3rem 0.6rem', borderRadius: '4px' }}>{slug}</code>
              </p>
            </div>
          </section>
        </main>
      </section>
    </div>
  );
}
