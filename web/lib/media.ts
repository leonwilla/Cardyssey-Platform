/**
 * Central place for every replaceable image on the homepage.
 * Swap the `src` values for authentic Pokémon TCG artwork or real CARDYSSEY
 * app screenshots – components read from here and need no changes.
 */

export type MediaAsset = {
  src: string
  alt: string
}

export const media = {
  community: {
    src: '/images/community.jpg',
    alt: 'Freunde sitzen am Tisch und zeigen sich gegenseitig ihre Sammelkarten',
  },
  shop: {
    src: '/images/shop.jpg',
    alt: 'Booster-Packs, Kartenhüllen und ein Sammelordner auf einem hellen Tisch',
  },
  scan: {
    src: '/images/scan.jpg',
    alt: 'Hand hält ein Smartphone über eine Sammelkarte, um sie einzuscannen',
  },
} satisfies Record<string, MediaAsset>

/**
 * Optional real app screenshots for the scrollytelling steps.
 * When a value is set, it replaces the illustrated preview for that step.
 * Upload validated screenshots under public/app-screenshots/ and use those paths.
 * Prefer cropped screenshots with no personal information, and verify source fidelity.
 */
export const appScreenshots: Record<'scannen' | 'sammeln' | 'marktpreise' | 'wunschliste', MediaAsset | null> = {
  scannen: null,
  sammeln: null,
  marktpreise: null,
  wunschliste: null,
}
