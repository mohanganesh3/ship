/**
 * Maritime AI — Design System v2 "Warm Charcoal"
 *
 * Inspired by ChatGPT's warm dark greys + Claude's editorial warmth.
 * NO monotone navy. NO uniform borders. Proper contrast hierarchy.
 */

// ─── COLOR SCALE ─────────────────────────────────────────────
export const Colors = {
  // Dark mode surfaces (warm charcoal, NOT navy)
  bg0:        '#141414',   // Deepest — behind everything
  bg1:        '#1A1A1A',   // Page background
  bg2:        '#242424',   // Surface — cards, input area, sidebar
  bg3:        '#2E2E2E',   // Elevated — user bubbles, hover states
  bg4:        '#383838',   // Active states, selected items

  // Borders (use sparingly)
  border1:    '#2E2E2E',   // Subtle — dividers between sections
  border2:    '#3A3A3A',   // Medium — input field outline
  border3:    '#4A4A4A',   // Strong — focus state

  // Text (warm off-white scale)
  text1:      '#ECECEC',   // Primary — headings, message body
  text2:      '#B4B4A9',   // Secondary — previews, descriptions
  text3:      '#8A897E',   // Tertiary — timestamps, metadata, hints
  text4:      '#5C5B52',   // Quaternary — placeholders, disabled

  // Light mode
  lightBg1:   '#FAF9F5',   // Page background — warm paper
  lightBg2:   '#F0EDE6',   // Surface — cards, input
  lightBg3:   '#E6E2DA',   // Elevated — user bubbles
  lightText1: '#1F1E1D',   // Primary text
  lightText2: '#5C5B52',   // Secondary
  lightText3: '#8A897E',   // Tertiary
  lightBorder:'#E2DDD3',   // Subtle borders

  // Accents
  amber:      '#D4943A',   // Primary CTA, send button
  amberDim:   '#B07D32',   // Dimmed amber for light mode
  danger:     '#D4534B',   // Safety — softer than pure red
  dangerDim:  'rgba(212, 83, 75, 0.12)', // Background for safety cards
  success:    '#4CAF72',   // Model active indicator
  thinking:   '#C9A84C',   // Thinking state text
  thinkingDim:'rgba(201, 168, 76, 0.08)', // Thinking block bg
} as const;

// ─── SEMANTIC THEME TOKENS ───────────────────────────────────
export const DarkTheme = {
  bgPage:        Colors.bg1,
  bgSurface:     Colors.bg2,
  bgElevated:    Colors.bg3,
  bgActive:      Colors.bg4,
  bgUserBubble:  Colors.bg3,
  bgInput:       Colors.bg2,
  borderSubtle:  Colors.border1,
  borderMedium:  Colors.border2,
  borderFocus:   Colors.border3,
  text1:         Colors.text1,
  text2:         Colors.text2,
  text3:         Colors.text3,
  text4:         Colors.text4,
  tabBarBg:      Colors.bg0,
} as const;

export const LightTheme = {
  bgPage:        Colors.lightBg1,
  bgSurface:     Colors.lightBg2,
  bgElevated:    Colors.lightBg3,
  bgActive:      '#D9D4CB',
  bgUserBubble:  Colors.lightBg3,
  bgInput:       '#FFFFFF',
  borderSubtle:  Colors.lightBorder,
  borderMedium:  '#D6D1C7',
  borderFocus:   '#C4BEB3',
  text1:         Colors.lightText1,
  text2:         Colors.lightText2,
  text3:         Colors.lightText3,
  text4:         '#ADA89E',
  tabBarBg:      Colors.lightBg1,
} as const;

export type ThemeColors = typeof DarkTheme | typeof LightTheme;

// ─── TYPOGRAPHY ──────────────────────────────────────────────
// DM Serif Display: display only (greeting, screen titles)
// Source Sans 3: everything else (body, labels, UI text)
// IBM Plex Mono: ONLY inside thinking blocks and technical readouts
export const Fonts = {
  display:       'DMSerifDisplay',
  body:          'SourceSans3',
  bodyLight:     'SourceSans3Light',
  bodySemibold:  'SourceSans3SemiBold',
  mono:          'IBMPlexMono',
} as const;

export const Type = {
  xs:    { fontSize: 12, lineHeight: 16 },     // timestamps
  sm:    { fontSize: 13, lineHeight: 18 },     // captions, hints
  base:  { fontSize: 16, lineHeight: 25.6 },   // message body (was 15 — too tight)
  md:    { fontSize: 17, lineHeight: 24 },      // UI labels, thread titles
  lg:    { fontSize: 20, lineHeight: 26 },      // section headers
  xl:    { fontSize: 24, lineHeight: 30 },      // screen titles
  '2xl': { fontSize: 30, lineHeight: 36 },      // display greeting
} as const;

// ─── SPACING (varied rhythm, NOT uniform) ────────────────────
export const Space = {
  xs:   4,
  sm:   8,
  md:   12,
  lg:   16,
  xl:   24,
  '2xl': 32,
  '3xl': 48,
  '4xl': 64,

  // Semantic spacing
  messageGap:     20,    // Between messages (generous)
  sectionGap:     32,    // Between major sections
  screenPadding:  20,    // Horizontal page padding (was 16, too tight on phone)
  cardPadding:    16,    // Internal card padding
  inputHeight:    52,    // Input tray min height
  inputMaxHeight: 140,   // Input max expand
  tabBarHeight:   56,    // Tab bar
  tapTarget:      44,    // Minimum tap target (iOS standard)
} as const;

// ─── BORDER RADIUS ───────────────────────────────────────────
export const Radius = {
  xs:   4,     // Small elements
  sm:   8,     // Thinking block
  md:   12,    // Cards
  lg:   16,    // User messages
  xl:   20,    // Input pill
  full: 9999,  // Circles
} as const;

// ─── QUICK-START CATEGORIES ──────────────────────────────────
export const QuickStartCategories = [
  {
    id: 'engine',
    title: 'Engine Diagnostics',
    description: 'Troubleshoot main and auxiliary engine issues',
    icon: 'engine-block',
    prompt: 'I need help diagnosing an issue with the main engine. ',
  },
  {
    id: 'safety',
    title: 'Safety Procedures',
    description: 'Emergency response and drill procedures',
    icon: 'lifebuoy',
    prompt: 'Walk me through the safety procedure for ',
  },
  {
    id: 'marpol',
    title: 'MARPOL Compliance',
    description: 'Pollution prevention and emission regulations',
    icon: 'compass',
    prompt: 'What are the MARPOL regulations regarding ',
  },
  {
    id: 'auxiliary',
    title: 'Auxiliary Systems',
    description: 'Pumps, purifiers, compressors, and generators',
    icon: 'gear',
    prompt: 'Help me troubleshoot the auxiliary system for ',
  },
] as const;

// ─── LOADING PHRASES ─────────────────────────────────────────
export const LoadingPhrases = [
  'Warming up the engine room...',
  'Checking the logbook...',
  'Standing by on the bridge...',
] as const;
