export type AdminMenuItem = {
  label: string;
  href: string;
  slug?: string;
  resource?: string;
  requiredGroups?: string[];
};

const GROUPS = {
  admins: 'admins',
  devs: 'devs',
  programmateur: 'programmateur',
} as const;

export const ADMIN_MENU: AdminMenuItem[] = [
  {
    label: 'Accueil',
    href: '/dashboard',
    resource: 'dashboard',
    requiredGroups: [GROUPS.admins, GROUPS.devs, GROUPS.programmateur],
  },
  {
    label: 'Tableaux de bord',
    href: '/dashboard/overview',
    slug: 'overview',
    resource: 'overview',
    requiredGroups: [GROUPS.admins, GROUPS.devs, GROUPS.programmateur],
  },
  {
    label: 'Contenu',
    href: '/dashboard/contenu',
    slug: 'contenu',
    resource: 'contenu',
    requiredGroups: [GROUPS.admins, GROUPS.programmateur],
  },
  {
    label: 'Chroniques Assistées',
    href: '/dashboard/chroniques-assistees',
    slug: 'chroniques-assistees',
    resource: 'chroniques-assistees',
    requiredGroups: [GROUPS.admins, GROUPS.programmateur],
  },
  {
    label: 'Chroniques Automatiques',
    href: '/dashboard/chroniques-automatiques',
    slug: 'chroniques-automatiques',
    resource: 'chroniques-automatiques',
    requiredGroups: [GROUPS.admins, GROUPS.programmateur],
  },
  {
    label: 'Chronique collaborative',
    href: '/dashboard/chronique-collaborative',
    slug: 'chronique-collaborative',
    resource: 'chronique-collaborative',
    requiredGroups: [GROUPS.admins, GROUPS.programmateur],
  },
  {
    label: 'Fichiers audio téléchargés',
    href: '/dashboard/fichiers-audio',
    slug: 'fichiers-audio',
    resource: 'fichiers-audio',
    requiredGroups: [GROUPS.admins, GROUPS.programmateur],
  },
  {
    label: 'Chroniques Universelles',
    href: '/dashboard/chroniques-universelles',
    slug: 'chroniques-universelles',
    resource: 'chroniques-universelles',
    requiredGroups: [GROUPS.admins, GROUPS.programmateur],
  },
  {
    label: 'Chroniques Studio',
    href: '/dashboard/chroniques-studio',
    slug: 'chroniques-studio',
    resource: 'chroniques-studio',
    requiredGroups: [GROUPS.admins, GROUPS.programmateur],
  },
  {
    label: 'Habillage d’Antenne',
    href: '/dashboard/habillage-antenne',
    slug: 'habillage-antenne',
    resource: 'habillage-antenne',
    requiredGroups: [GROUPS.admins, GROUPS.programmateur],
  },
  {
    label: 'Playlists',
    href: '/dashboard/playlists',
    slug: 'playlists',
    resource: 'playlists',
    requiredGroups: [GROUPS.admins, GROUPS.programmateur],
  },
  {
    label: 'Debug API',
    href: '/dashboard/debug-api',
    slug: 'debug-api',
    resource: 'debug-api',
    requiredGroups: [GROUPS.admins, GROUPS.devs],
  },
  {
    label: 'Programmations',
    href: '/dashboard/programmations',
    slug: 'programmations',
    resource: 'programmations',
    requiredGroups: [GROUPS.admins, GROUPS.programmateur],
  },
  {
    label: 'Statistiques',
    href: '/dashboard/statistiques',
    slug: 'statistiques',
    resource: 'statistiques',
    requiredGroups: [GROUPS.admins, GROUPS.devs, GROUPS.programmateur],
  },
  {
    label: 'Cache',
    href: '/api/admin/cache',
    resource: 'cache',
    requiredGroups: [GROUPS.admins, GROUPS.devs],
  },
];

export function findMenuBySlug(slug: string) {
  return ADMIN_MENU.find((item) => item.slug === slug);
}

type IamGroupsByResource = Record<string, string[]>;

function parseCsv(raw?: string): string[] {
  if (!raw) return [];
  return raw.split(',').map((s) => s.trim()).filter(Boolean);
}

function toResourceKey(resource?: string): string {
  if (!resource) return '*';
  return resource.trim().toLowerCase();
}

function parseIamRules(raw?: string): IamGroupsByResource {
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};

    const out: IamGroupsByResource = {};
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (Array.isArray(value)) {
        const groups = value.filter((g): g is string => typeof g === 'string').map((g) => g.trim()).filter(Boolean);
        if (groups.length > 0) out[toResourceKey(key)] = groups;
      } else if (typeof value === 'string') {
        const groups = parseCsv(value);
        if (groups.length > 0) out[toResourceKey(key)] = groups;
      }
    }

    return out;
  } catch {
    return {};
  }
}

const IAM_RULES = parseIamRules(process.env.NEXT_PUBLIC_IAM_GROUP_RULES);

export function extractIamGroups(profile?: Record<string, unknown> | null): string[] {
  if (!profile) return [];

  const value = profile['cognito:groups'] ?? profile.groups;
  if (Array.isArray(value)) {
    return value.filter((v): v is string => typeof v === 'string').map((v) => v.trim()).filter(Boolean);
  }
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((v) => v.trim())
      .filter(Boolean);
  }

  return [];
}

function getRequiredGroups(item: AdminMenuItem): string[] {
  if (item.requiredGroups && item.requiredGroups.length > 0) return item.requiredGroups;

  const resourceKey = toResourceKey(item.resource);
  if (IAM_RULES[resourceKey]?.length) return IAM_RULES[resourceKey];
  if (IAM_RULES['*']?.length) return IAM_RULES['*'];

  // Backward compatibility for existing cache restriction env.
  if (resourceKey === 'cache') {
    return parseCsv(process.env.NEXT_PUBLIC_ALLOWED_PROGRAMMATEUR_GROUPS ?? 'programmateur');
  }

  return [];
}

export function canAccessMenuItem(item: AdminMenuItem, profile?: Record<string, unknown> | null): boolean {
  const required = getRequiredGroups(item);
  if (required.length === 0) return true;

  const userGroups = extractIamGroups(profile);
  return userGroups.some((group) => required.includes(group));
}

export function canAccessResource(resource: string, profile?: Record<string, unknown> | null): boolean {
  const item = ADMIN_MENU.find((menuItem) => menuItem.resource === resource || menuItem.slug === resource);
  if (!item) {
    if (IAM_RULES['*']?.length) {
      const userGroups = extractIamGroups(profile);
      return userGroups.some((group) => IAM_RULES['*'].includes(group));
    }
    return true;
  }

  return canAccessMenuItem(item, profile);
}

export function filterMenuByAccess(profile?: Record<string, unknown> | null): AdminMenuItem[] {
  return ADMIN_MENU.filter((item) => canAccessMenuItem(item, profile));
}

export function firstAccessibleMenuHref(profile?: Record<string, unknown> | null): string {
  const visible = filterMenuByAccess(profile);
  return visible[0]?.href ?? '/dashboard';
}
