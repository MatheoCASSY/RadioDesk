"use client";

import Image from 'next/image';
import Link from 'next/link';
import React from 'react';
import type { AdminMenuItem } from './menu';

type DashboardShellProps = {
  visibleMenu: AdminMenuItem[];
  activeSlug?: string;
  activeHref?: string;
  topbarTag: string;
  liveTitle: string;
  pageTitle: React.ReactNode;
  userLabel: string;
  onLogout: () => void;
  breadcrumbs?: React.ReactNode;
  children: React.ReactNode;
};

export default function DashboardShell({
  visibleMenu,
  activeSlug,
  activeHref,
  topbarTag,
  liveTitle,
  pageTitle,
  userLabel,
  onLogout,
  breadcrumbs,
  children,
}: DashboardShellProps) {
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
          <div className="fluff-live-title">{liveTitle}</div>
          <div className="fluff-live-ready">READY</div>
        </div>

        <nav className="fluff-nav">
          {visibleMenu.map((item) => {
            const isActive = item.slug === activeSlug || item.href === activeHref;
            return (
              <Link
                key={item.slug || item.resource || item.href}
                className={`fluff-nav-item ${isActive ? 'active' : ''}`}
                href={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <section className="fluff-dashboard-main">
        <div className="fluff-topbar">
          <div className="fluff-topbar-tag">{topbarTag}</div>
          <div className="fluff-topbar-user">
            <span className="fluff-topbar-name">{userLabel}</span>
            <button className="fluff-topbar-logout" onClick={onLogout}>Déconnexion</button>
          </div>
        </div>

        <main className="fluff-content">
          <h1 className="fluff-page-title">{pageTitle}</h1>
          {breadcrumbs ? <div className="fluff-breadcrumbs">{breadcrumbs}</div> : null}
          {children}
        </main>
      </section>
    </div>
  );
}